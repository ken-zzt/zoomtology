"""레거시 PHP 추출기 — zoomzoom-admin · zoomzoom-partners (2단계, ZDV-346).

산출: Module(php-area)·File·CodeUnit(class/method/function)·Route(opencart)·READS/WRITES·JOINS·REFERENCES(logical)·
CALLS(zoomtu/model/self/static/controller)·EnumValue(code-static-array)·PUBLISHES(heuristic)·Database/Table(다른 DB 핸들).
SQL 텍스트는 테이블 토큰을 뽑은 뒤 바로 버린다. 코드 본문·자격증명 경로는 읽지 않는다 (schema.yaml content_guard).
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import model, phplex, sqlshape
from .collect import Collector, edge_rec, node_rec
from .guard import is_denied_path
from .schema import Schema
from .sources import SERVICE

SOURCE = "php@1"

# 저장소별로 읽는 영역. (영역 경로, 재귀 여부). 뷰·언어 파일·vendor 는 읽지 않는다.
AREAS: dict[str, list[tuple[str, bool]]] = {
    "zoomzoom-admin": [("admin/controller", True), ("admin/model", True), ("catalog/controller", True), ("catalog/model", True),
                       ("system/library/zoomtu", True), ("system/library", False)],
    "zoomzoom-partners": [("catalog/controller", True), ("catalog/model", True), ("system/library/zoomtu", True), ("system/library", False)],
}
# DB 핸들 → Database uid 의 handle. read_db 는 운영 DB 읽기 복제본이라 같은 zzt.
HANDLE_DB = {"db": "zzt", "read_db": "zzt", "numbers_db": "numbers", "stats_db": "stats", "task_db": "stats-task"}
# 클래스 static 배열 이름 → (테이블, 컬럼). 코드 enum 을 컬럼에 거는 유일한 규칙. 큐레이션이 4단계에서 덮어쓸 수 있다.
STATIC_ENUM_MAP = {"order_status_string": ("zoom_order", "order_status_id")}
SENSITIVE_RE = re.compile(r"(?i)password|secret|token|api[_-]?key|credential")
QUEUE_CONST_RE = re.compile(r"^SEND_([A-Z_]+)_QUEUE$")
# PHP 의 SEND_<X>_QUEUE 상수 → message-consumer 역할(큐 이름 꼬리). 근거: devenv/templates/nginx/zzt/*.env.conf.tmpl,
# zoomzoom-services/docs/40-local-dev/devenv-architecture.md (SEND_PUSH_QUEUE → `-notif`). LAMBDA 는 zoomzoom-api 의 `dev-zzt-api` 큐.
QUEUE_ROLE = {"ORDER": "order", "EMAIL": "email", "EVENT": "event", "PUSH": "notif", "LAMBDA": "lambda"}
MAX_EXAMPLES = 5


@dataclass
class RepoSpec:
    name: str
    root: Path
    areas: list[tuple[str, bool]]


def default_repos() -> list[RepoSpec]:
    return [RepoSpec(name, SERVICE / name, areas) for name, areas in AREAS.items()]


@dataclass
class _Unit:
    uid: str
    cls: str | None
    method: phplex.Method | None
    func: phplex.FunctionDef | None
    file_rel: str


@dataclass
class _Index:
    """저장소 하나의 클래스·메서드 색인. 호출 해석과 placeholder 판단에 쓴다."""
    classes: dict[str, tuple[str, phplex.ClassDef]] = field(default_factory=dict)       # Class → (file_rel, def)
    zoomtu: dict[str, tuple[str, str]] = field(default_factory=dict)                     # zzt_x → (file_rel, Class)
    models: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)          # area(admin|catalog) → model_a_b → (file_rel, Class)
    controllers: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)     # area → a/b → (file_rel, Class)

    def has_method(self, cls: str, method: str, depth: int = 0) -> str | None:
        """메서드를 가진 클래스 이름(부모까지 올라간다). 없으면 None."""
        entry = self.classes.get(cls)
        if not entry or depth > 8:
            return None
        _, cdef = entry
        if any(m.name == method for m in cdef.methods):
            return cls
        if cdef.parent:
            return self.has_method(cdef.parent, method, depth + 1)
        return None


@dataclass
class _Stats:
    files: int = 0
    classes: int = 0
    units: int = 0
    queries: int = 0
    zero_table: list[str] = field(default_factory=list)      # SQL 에 테이블 자리가 아예 없음 (헬퍼 조립·SHOW 등)
    unknown_only: int = 0                                     # 테이블 이름은 있는데 전부 스키마에 없음 (폐기 테이블)
    dynamic: list[str] = field(default_factory=list)
    unknown_receiver: Counter = field(default_factory=Counter)
    unknown_table: Counter = field(default_factory=Counter)
    unresolved: Counter = field(default_factory=Counter)
    placeholders: int = 0
    queue_roles: Counter = field(default_factory=Counter)
    no_key_publish: list[str] = field(default_factory=list)


# --- 파일 수집 ----------------------------------------------------------------

def _iter_files(spec: RepoSpec, schema: Schema) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for area, recursive in spec.areas:
        base = spec.root / area
        if not base.is_dir():
            continue
        paths = base.rglob("*.php") if recursive else base.glob("*.php")
        for p in sorted(paths):
            rel = p.relative_to(spec.root).as_posix()
            if rel in seen or is_denied_path(f"{spec.name}/{rel}", schema):
                continue
            seen.add(rel)
            out.append((rel, p))
    return out


def _area_of(rel: str) -> str:
    """파일이 속한 php-area (module uid 의 꼬리)."""
    if rel.startswith("system/library/zoomtu/"):
        return "system/library/zoomtu"
    if rel.startswith("system/library/"):
        return "system/library"
    parts = rel.split("/")
    return "/".join(parts[:2])


def _app_of(rel: str) -> str | None:
    return rel.split("/", 1)[0] if rel.startswith(("admin/", "catalog/")) else None


# --- 색인 -----------------------------------------------------------------------

def _build_index(files: list[tuple[str, phplex.FileStructure]]) -> _Index:
    idx = _Index()
    for rel, fs in files:
        for c in fs.classes:
            if c.name in idx.classes:
                continue        # 같은 이름이 또 있으면 먼저 본 것 (report 에서 다루지 않는다 — 드묾)
            idx.classes[c.name] = (rel, c)
        if not fs.classes:
            continue
        main = fs.classes[0].name
        if rel.startswith("system/library/zoomtu/"):
            key = "zzt_" + rel[len("system/library/zoomtu/"):-4].replace("/", "_")
            idx.zoomtu[key] = (rel, main)
        app = _app_of(rel)
        if app and rel.startswith(f"{app}/model/"):
            key = "model_" + rel[len(f"{app}/model/"):-4].replace("/", "_")
            idx.models.setdefault(app, {})[key] = (rel, main)
        elif app and rel.startswith(f"{app}/controller/"):
            key = rel[len(f"{app}/controller/"):-4]
            idx.controllers.setdefault(app, {})[key] = (rel, main)
    return idx


# --- 표현식 → 텍스트 (SQL 모양) ----------------------------------------------------

def _match_close(toks: list[phplex.Tok], i: int, open_: str, close: str) -> int:
    return phplex._match_close(toks, i, open_, close)


def _split_args(toks: list[phplex.Tok]) -> list[list[phplex.Tok]]:
    args: list[list[phplex.Tok]] = []
    cur: list[phplex.Tok] = []
    depth = 0
    for t in toks:
        if t.kind == "punct":
            if t.text in ("(", "["):
                depth += 1
            elif t.text in (")", "]"):
                depth -= 1
            elif t.text == "," and depth == 0:
                args.append(cur)
                cur = []
                continue
        cur.append(t)
    if cur:
        args.append(cur)
    return args


def _eval(toks: list[phplex.Tok], env: dict[str, str]) -> str:
    """문자열 리터럴만 이어붙인다. 변수는 같은 메서드 안의 대입 텍스트로, 그 밖은 ` ? ` 로."""
    out: list[str] = []
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.kind == "str":
            out.append(t.text)
            i += 1
        elif t.kind == "num":
            out.append(t.text)
            i += 1
        elif t.kind == "ident" and t.text == "DB_PREFIX":
            out.append("zoom_")
            i += 1
        elif t.kind == "var":
            if i + 1 < n and toks[i + 1].kind == "punct" and toks[i + 1].text in ("->", "?->", "::"):
                # 멤버 접근 체인: $this->x->y(...) 전부 건너뛴다
                j = i + 1
                while j < n and toks[j].kind == "punct" and toks[j].text in ("->", "?->", "::"):
                    j += 1
                    if j < n and toks[j].kind in ("ident", "var"):
                        j += 1
                    if j < n and toks[j].kind == "punct" and toks[j].text == "(":
                        j = _match_close(toks, j, "(", ")") + 1
                    while j < n and toks[j].kind == "punct" and toks[j].text == "[":
                        j = _match_close(toks, j, "[", "]") + 1
                out.append(" ? ")
                i = j
            elif i + 1 < n and toks[i + 1].kind == "punct" and toks[i + 1].text == "[":
                j = i + 1
                while j < n and toks[j].kind == "punct" and toks[j].text == "[":
                    j = _match_close(toks, j, "[", "]") + 1
                out.append(" ? ")
                i = j
            else:
                out.append(env.get(t.text, " ? "))
                i += 1
        elif t.kind == "ident" and i + 1 < n and toks[i + 1].kind == "punct" and toks[i + 1].text == "(":
            end = _match_close(toks, i + 1, "(", ")")
            if t.text in ("sprintf", "vsprintf"):
                args = _split_args(toks[i + 2:end])
                if args:
                    out.append(_eval(args[0], env))
            out.append(" ? ")
            i = end + 1
        elif t.kind == "punct" and t.text in ("(", ")", "."):
            i += 1
        elif t.kind == "punct" and t.text in ("?", ":"):
            out.append(" ")
            i += 1
        else:
            out.append(" ? ")
            i += 1
    return "".join(out)


# --- 메서드 몸통 분석 ----------------------------------------------------------------

@dataclass
class _Query:
    line: int
    handle: str
    text: str


@dataclass
class _Call:
    line: int
    kind: str          # zoomtu | model | self | static | controller
    target: str        # zzt_x / model_a_b / method / Class / a/b/c
    method: str | None


@dataclass
class _Publish:
    line: int
    key: str | None
    queue_const: str | None


@dataclass
class _BodyFacts:
    queries: list[_Query] = field(default_factory=list)
    calls: list[_Call] = field(default_factory=list)
    publishes: list[_Publish] = field(default_factory=list)
    unknown_receiver: Counter = field(default_factory=Counter)


def _is(t: phplex.Tok, kind: str, text: str | None = None) -> bool:
    return t.kind == kind and (text is None or t.text == text)


def analyze_body(body: list[phplex.Tok]) -> _BodyFacts:
    facts = _BodyFacts()
    env: dict[str, str] = {}
    for st in phplex.statements(body):
        n = len(st)
        # 1. `$var = …` / `$var .= …`
        if n >= 3 and st[0].kind == "var" and _is(st[1], "punct", "=") and not (n > 3 and _is(st[2], "punct", "&")):
            env[st[0].text] = _eval(st[2:], env)
        elif n >= 3 and st[0].kind == "var" and _is(st[1], "punct", ".="):
            env[st[0].text] = env.get(st[0].text, " ? ") + _eval(st[2:], env)
        # 2. 호출·쿼리 패턴
        i = 0
        while i < n:
            t = st[i]
            # ->query( / ->task_db_query(
            if t.kind == "ident" and t.text in ("query", "task_db_query") and i + 1 < n and _is(st[i + 1], "punct", "(") \
                    and i >= 1 and _is(st[i - 1], "punct", "->"):
                handle = None
                recv = st[i - 2] if i >= 2 else None
                if t.text == "task_db_query":
                    handle = "task_db"
                elif recv is not None and recv.kind == "ident" and recv.text in HANDLE_DB:
                    handle = recv.text
                elif recv is not None and recv.kind == "var" and recv.text[1:] in HANDLE_DB:
                    handle = recv.text[1:]
                elif recv is not None and _is(recv, "punct", ")") and i >= 5 and _is(st[i - 5], "ident", "getReadDb"):
                    handle = "read_db"
                end = _match_close(st, i + 1, "(", ")")
                if handle:
                    args = _split_args(st[i + 2:end])
                    facts.queries.append(_Query(t.line, handle, _eval(args[0], env) if args else ""))
                else:
                    facts.unknown_receiver[recv.text if recv is not None else "?"] += 1
                i = end + 1
                continue
            # $this->X->m(   /  $this->m(
            if t.kind == "var" and t.text == "$this" and i + 2 < n and _is(st[i + 1], "punct", "->") and st[i + 2].kind == "ident":
                a = st[i + 2].text
                if i + 4 < n and _is(st[i + 3], "punct", "->") and st[i + 4].kind == "ident" and i + 5 < n and _is(st[i + 5], "punct", "(") \
                        and a not in HANDLE_DB:
                    m = st[i + 4].text
                    if a.startswith("zzt_"):
                        facts.calls.append(_Call(t.line, "zoomtu", a, m))
                        if m == "sendMessage":
                            facts.publishes.append(_parse_publish(st, i + 5, t.line))
                    elif a.startswith("model_"):
                        facts.calls.append(_Call(t.line, "model", a, m))
                    elif a == "load" and m == "controller":
                        end = _match_close(st, i + 5, "(", ")")
                        args = _split_args(st[i + 6:end])
                        if args and len(args[0]) == 1 and args[0][0].kind == "str":
                            facts.calls.append(_Call(t.line, "controller", args[0][0].text, None))
                    i += 5
                    continue
                if i + 3 < n and _is(st[i + 3], "punct", "(") and a not in ("load",):
                    facts.calls.append(_Call(t.line, "self", a, a))
                    i += 3
                    continue
            # self::m( / static::m( / Class::m(
            if t.kind == "ident" and i + 3 < n and _is(st[i + 1], "punct", "::") and st[i + 2].kind == "ident" and _is(st[i + 3], "punct", "("):
                if t.text in ("self", "static", "parent"):
                    facts.calls.append(_Call(t.line, "self", t.text, st[i + 2].text))
                else:
                    facts.calls.append(_Call(t.line, "static", t.text, st[i + 2].text))
                i += 3
                continue
            i += 1
    return facts


def _parse_publish(st: list[phplex.Tok], open_idx: int, line: int) -> _Publish:
    end = _match_close(st, open_idx, "(", ")")
    args = _split_args(st[open_idx + 1:end])
    key = None
    if args:
        a0 = args[0]
        for k in range(len(a0) - 2):
            if _is(a0[k], "str", "key") and _is(a0[k + 1], "punct", "=>") and a0[k + 2].kind == "str":
                key = a0[k + 2].text
                break
    const = None
    if len(args) > 1:
        for t in args[1]:
            if t.kind == "ident" and QUEUE_CONST_RE.match(t.text):
                const = t.text
                break
    return _Publish(line, key, const)


# --- 추출 본체 -----------------------------------------------------------------------

def extract(col: Collector, repos: list[RepoSpec] | None = None, schema: Schema | None = None) -> dict[str, str]:
    schema = schema or Schema.load()
    repos = repos if repos is not None else default_repos()
    known_tables = {uid[len("table:"):] for uid in col.nodes if uid.startswith("table:") and "/" not in uid}
    col.sections.setdefault("php", [])
    meta: dict[str, str] = {}
    for spec in repos:
        if not spec.root.is_dir():
            col.warn(SOURCE, f"{spec.name}: repo not found at {spec.root}")
            continue
        stats = _extract_repo(col, spec, schema, known_tables)
        meta[spec.name] = f"files={stats.files} classes={stats.classes} units={stats.units} queries={stats.queries}"
        _report(col, spec.name, stats)
    return meta


def _extract_repo(col: Collector, spec: RepoSpec, schema: Schema, known_tables: set[str]) -> _Stats:
    stats = _Stats()
    repo = spec.name
    parsed: list[tuple[str, phplex.FileStructure, int, str]] = []
    for rel, path in _iter_files(spec, schema):
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            col.warn(SOURCE, f"{repo}/{rel}: {e}")
            continue
        toks = phplex.tokenize(src)
        parsed.append((rel, phplex.parse(toks), src.count("\n") + 1, hashlib.sha1(src.encode("utf-8", "replace")).hexdigest()))
    idx = _build_index([(rel, fs) for rel, fs, _, _ in parsed])
    stats.files = len(parsed)

    joins: dict[tuple[str, str], dict] = {}
    refs: dict[tuple[str, str], dict] = {}
    modules: set[str] = set()

    for rel, fs, loc, sha1 in parsed:
        area = _area_of(rel)
        muid = f"module:{repo}/{area}"
        if muid not in modules:
            modules.add(muid)
            col.node(node_rec(muid, "Module", area, SOURCE, props={"kind": "php-area", "repo": repo, "path": area}, source_ref=f"{repo}/{area}"))
            col.edge(edge_rec(model.repo_uid(repo), "CONTAINS", muid, SOURCE, source_ref=f"{repo}/{area}"))
        fuid = model.file_uid(repo, rel)
        col.node(node_rec(fuid, "File", rel.rsplit("/", 1)[-1], SOURCE,
                          props={"repo": repo, "path": rel, "lang": "php", "loc": loc, "sha1": sha1, "area": area}, source_ref=f"{repo}/{rel}"))
        col.edge(edge_rec(muid, "CONTAINS", fuid, SOURCE, source_ref=f"{repo}/{rel}"))
        app = _app_of(rel)
        is_controller = app is not None and rel.startswith(f"{app}/controller/")
        is_model = app is not None and rel.startswith(f"{app}/model/")

        for c in fs.classes:
            stats.classes += 1
            cuid = model.code_uid(repo, rel, c.name)
            kind = "controller" if is_controller else "model" if is_model else "class"
            props = {"kind": kind, "lineStart": c.line_start, "lineEnd": c.line_end, "methodCount": len(c.methods)}
            if c.parent:
                props["parent"] = c.parent
            if fs.namespace:
                props["namespace"] = fs.namespace
            flat = {sa.name: dict(sa.items) for sa in c.static_arrays if sa.flat and sa.items
                    and not SENSITIVE_RE.search(sa.name) and not any(SENSITIVE_RE.search(k) or SENSITIVE_RE.search(v) for k, v in sa.items)
                    and all(len(k) <= 80 and len(v) <= 200 for k, v in sa.items)}
            if flat:
                props["staticArrays"] = flat
            col.node(node_rec(cuid, "CodeUnit", c.name, SOURCE, props=props, source_ref=f"{repo}/{rel}:{c.line_start}-{c.line_end}"))
            col.edge(edge_rec(fuid, "CONTAINS", cuid, SOURCE, source_ref=f"{repo}/{rel}:{c.line_start}"))
            stats.units += 1
            _static_enums(col, cuid, c, repo, rel, known_tables)

            route_base = rel[len(f"{app}/controller/"):-4] if is_controller else None
            for m in c.methods:
                stats.units += 1
                uid = model.code_uid(repo, rel, c.name, m.name)
                mprops = {"kind": "method", "lineStart": m.line_start, "lineEnd": m.line_end, "visibility": m.visibility, "class": c.name}
                if m.is_static:
                    mprops["isStatic"] = True
                if m.abstract:
                    mprops["abstract"] = True
                col.node(node_rec(uid, "CodeUnit", f"{c.name}::{m.name}", SOURCE, props=mprops, source_ref=f"{repo}/{rel}:{m.line_start}-{m.line_end}"))
                col.edge(edge_rec(fuid, "CONTAINS", uid, SOURCE, source_ref=f"{repo}/{rel}:{m.line_start}"))
                if route_base and m.visibility == "public" and not m.name.startswith("_") and not m.is_static:
                    for rpath in ([f"{route_base}/{m.name}", route_base] if m.name == "index" else [f"{route_base}/{m.name}"]):
                        ruid = model.opencart_route_uid(repo, rpath)
                        col.node(node_rec(ruid, "Route", rpath, SOURCE, props={"repo": repo, "kind": "opencart", "path": rpath, "area": app},
                                          source_ref=f"{repo}/{rel}:{m.line_start}"))
                        col.edge(edge_rec(uid, "HANDLES", ruid, SOURCE, source_ref=f"{repo}/{rel}:{m.line_start}"))
                if m.body:
                    _unit_facts(col, _Unit(uid, c.name, m, None, rel), analyze_body(m.body), repo, idx, app, known_tables, stats, joins, refs)
        for f in fs.functions:
            stats.units += 1
            uid = model.code_uid(repo, rel, f.name)
            col.node(node_rec(uid, "CodeUnit", f.name, SOURCE, props={"kind": "function", "lineStart": f.line_start, "lineEnd": f.line_end},
                              source_ref=f"{repo}/{rel}:{f.line_start}-{f.line_end}"))
            col.edge(edge_rec(fuid, "CONTAINS", uid, SOURCE, source_ref=f"{repo}/{rel}:{f.line_start}"))
            _unit_facts(col, _Unit(uid, None, None, f, rel), analyze_body(f.body), repo, idx, app, known_tables, stats, joins, refs)

    for (a, b), j in sorted(joins.items()):
        col.edge(edge_rec(model.table_uid(a), "JOINS", model.table_uid(b), SOURCE,
                          props={"count": j["count"], "examples": j["examples"], "onColumns": sorted(j["on"]), "repo": repo},
                          source_ref=j["examples"][0]))
    for (fc, tc), r in sorted(refs.items()):
        col.edge(edge_rec(fc, "REFERENCES", tc, SOURCE, props={"kind": "logical", "evidence": r["evidence"], "count": r["count"]},
                          source_ref=r["evidence"][0]))
    return stats


def _static_enums(col: Collector, cuid: str, c: phplex.ClassDef, repo: str, rel: str, known_tables: set[str]) -> None:
    for sa in c.static_arrays:
        if not sa.flat or sa.name not in STATIC_ENUM_MAP:
            continue
        table, column = STATIC_ENUM_MAP[sa.name]
        if table not in known_tables:
            continue
        cuid_col = model.col_uid(table, column)
        if cuid_col not in col.nodes:
            continue
        ref = f"{repo}/{rel}:{sa.line}"
        for value, meaning in sa.items:
            euid = model.enum_uid(table, column, value)
            col.node(node_rec(euid, "EnumValue", str(value), SOURCE, summary=meaning,
                              props={"value": str(value), "origin": "code-static-array", "meaning": meaning, "label": meaning,
                                     "definedIn": f"{c.name}::${sa.name}"}, source_ref=ref))
            col.edge(edge_rec(cuid_col, "HAS_VALUE", euid, SOURCE, source_ref=ref))
            col.edge(edge_rec(cuid, "DEFINES", euid, SOURCE, props={"array": sa.name}, source_ref=ref))


def _unit_facts(col: Collector, unit: _Unit, facts: _BodyFacts, repo: str, idx: _Index, app: str | None, known_tables: set[str],
                stats: _Stats, joins: dict, refs: dict) -> None:
    rel = unit.file_rel
    stats.unknown_receiver.update(facts.unknown_receiver)
    reads: dict[str, dict] = {}
    writes: dict[str, dict] = {}
    for q in facts.queries:
        stats.queries += 1
        sh = sqlshape.shape(q.text)
        ref = f"{repo}/{rel}:{q.line}"
        if sh.dynamic:
            stats.dynamic.append(ref)
        db = HANDLE_DB[q.handle]
        resolved: dict[str, set[str]] = {}
        for name, ops in sh.tables.items():
            if db == "zzt":
                if name in known_tables:
                    resolved[model.table_uid(name)] = ops
                else:
                    stats.unknown_table[name] += 1
            else:
                tuid = model.table_uid(name, db)
                _ensure_other_db_table(col, db, name, tuid, ref)
                resolved[tuid] = ops
        if not resolved:
            if sh.tables:
                stats.unknown_only += 1
            elif not sh.dynamic:
                stats.zero_table.append(ref)
        for tuid, ops in resolved.items():
            for op in ops:
                bucket = reads if op == "select" else writes
                e = bucket.setdefault(tuid, {"ops": set(), "lines": set(), "handles": set()})
                e["ops"].add(op)
                e["lines"].add(q.line)
                e["handles"].add(q.handle)
        if db == "zzt":
            zz = {a for a in sh.tables if a in known_tables}
            for a, b in sh.joins:
                if a in zz and b in zz:
                    j = joins.setdefault((a, b), {"count": 0, "examples": [], "on": set()})
                    j["count"] += 1
                    if len(j["examples"]) < MAX_EXAMPLES and ref not in j["examples"]:
                        j["examples"].append(ref)
            for (ta, ca), (tb, cb) in sh.on_pairs:
                if ta in zz and tb in zz:
                    key = tuple(sorted((ta, tb)))
                    if key in joins:
                        joins[key]["on"].add(f"{ta}.{ca}={tb}.{cb}" if ta <= tb else f"{tb}.{cb}={ta}.{ca}")
                    _logical_ref(col, refs, ta, ca, tb, cb, ref)
    for bucket, etype in ((reads, "READS"), (writes, "WRITES")):
        for tuid, e in bucket.items():
            col.edge(edge_rec(unit.uid, etype, tuid, SOURCE,
                              props={"ops": sorted(e["ops"]), "lines": sorted(e["lines"]), "handle": ",".join(sorted(e["handles"]))},
                              source_ref=f"{repo}/{rel}:{min(e['lines'])}"))

    calls: dict[str, dict] = {}
    for c in facts.calls:
        target = _resolve_call(c, unit, repo, idx, app, stats)
        if target is None:
            continue
        tuid, kind = target
        if tuid == unit.uid:
            continue
        e = calls.setdefault(tuid, {"kind": kind, "lines": set()})
        e["lines"].add(c.line)
    for tuid, e in calls.items():
        col.edge(edge_rec(unit.uid, "CALLS", tuid, SOURCE, props={"kind": e["kind"], "lines": sorted(e["lines"])},
                          source_ref=f"{repo}/{rel}:{min(e['lines'])}"))

    for p in facts.publishes:
        if not p.key:
            stats.no_key_publish.append(f"{repo}/{rel}:{p.line}")
            continue
        const_key = QUEUE_CONST_RE.match(p.queue_const).group(1) if p.queue_const else "LAMBDA"
        role = QUEUE_ROLE.get(const_key, const_key.lower().replace("_", ""))
        if const_key not in QUEUE_ROLE:
            col.warn(SOURCE, f"{repo}/{rel}:{p.line}: unknown queue const SEND_{const_key}_QUEUE — role guessed {role!r}")
        stats.queue_roles[role] += 1
        ref = f"{repo}/{rel}:{p.line}"
        quid = model.queue_uid(role)
        col.node(node_rec(quid, "Queue", role, SOURCE, props={"role": role, "queueConst": p.queue_const or "SEND_LAMBDA_QUEUE"}, source_ref=ref))
        muid = model.msg_uid(role, p.key)
        col.node(node_rec(muid, "QueueMessage", p.key, SOURCE, props={"queue": role, "key": p.key}, source_ref=ref))
        col.edge(edge_rec(unit.uid, "PUBLISHES", muid, SOURCE, props={"lines": [p.line], "heuristic": "sendMessage(['key'=>…], SEND_*_QUEUE)"}, source_ref=ref))


def _ensure_other_db_table(col: Collector, db: str, name: str, tuid: str, ref: str) -> None:
    duid = model.db_uid(db)
    if duid not in col.nodes:
        col.node(node_rec(duid, "Database", db, SOURCE, props={"handle": db, "engine": "mysql"}, source_ref=ref))
    if tuid not in col.nodes:
        col.node(node_rec(tuid, "Table", name, SOURCE, props={"db": db, "schemaKnown": False}, source_ref=ref))
        col.edge(edge_rec(duid, "CONTAINS", tuid, SOURCE, source_ref=ref))


def _logical_ref(col: Collector, refs: dict, ta: str, ca: str, tb: str, cb: str, ref: str) -> None:
    a, b = model.col_uid(ta, ca), model.col_uid(tb, cb)
    na, nb = col.nodes.get(a), col.nodes.get(b)
    if not na or not nb:
        return
    pa, pb = bool(na["props"].get("isPk")), bool(nb["props"].get("isPk"))
    if pa and not pb:
        a, b = b, a            # FK → PK 방향
    elif pa == pb and a > b:
        a, b = b, a
    r = refs.setdefault((a, b), {"count": 0, "evidence": []})
    r["count"] += 1
    if len(r["evidence"]) < MAX_EXAMPLES and ref not in r["evidence"]:
        r["evidence"].append(ref)


def _resolve_call(c: _Call, unit: _Unit, repo: str, idx: _Index, app: str | None, stats: _Stats) -> tuple[str, str] | None:
    """호출 대상 CodeUnit uid 와 CALLS.kind. 클래스는 있는데 메서드가 없으면 placeholder 를 만든다."""
    if c.kind == "zoomtu":
        entry = idx.zoomtu.get(c.target)
        if not entry:
            stats.unresolved[f"zoomtu:{c.target}"] += 1
            return None
        rel, cls = entry
        return _method_uid(repo, idx, rel, cls, c.method, stats), "zoomtu"
    if c.kind == "model":
        apps = [app] if app else (["admin", "catalog"] if repo == "zoomzoom-admin" else ["catalog"])
        for a in apps:
            entry = idx.models.get(a, {}).get(c.target)
            if entry:
                rel, cls = entry
                return _method_uid(repo, idx, rel, cls, c.method, stats), "model"
        stats.unresolved[f"model:{c.target}"] += 1
        return None
    if c.kind == "controller":
        apps = [app] if app else (["admin", "catalog"] if repo == "zoomzoom-admin" else ["catalog"])
        parts = c.target.strip("/").split("/")
        for a in apps:
            table = idx.controllers.get(a, {})
            if c.target in table:
                rel, cls = table[c.target]
                return _method_uid(repo, idx, rel, cls, "index", stats), "controller"
            if len(parts) >= 2 and "/".join(parts[:-1]) in table:
                rel, cls = table["/".join(parts[:-1])]
                return _method_uid(repo, idx, rel, cls, parts[-1], stats), "controller"
        stats.unresolved[f"controller:{c.target}"] += 1
        return None
    if c.kind == "self":
        if not unit.cls:
            return None
        owner = idx.has_method(unit.cls, c.method or "")
        if not owner:
            return None          # 프레임워크 부모(Model/Controller)의 메서드이거나 매직 메서드 — 관계 없음
        rel, _ = idx.classes[owner]
        return model.code_uid(repo, rel, owner, c.method), "self"
    if c.kind == "static":
        entry = idx.classes.get(c.target)
        if not entry:
            return None
        rel, cdef = entry
        return _method_uid(repo, idx, rel, cdef.name, c.method, stats), "static"
    return None


def _method_uid(repo: str, idx: _Index, rel: str, cls: str, method: str | None, stats: _Stats) -> str:
    method = method or "index"
    owner = idx.has_method(cls, method)
    if owner:
        orel, _ = idx.classes[owner]
        return model.code_uid(repo, orel, owner, method)
    stats.placeholders += 1
    return model.code_uid(repo, rel, cls, method)


def ensure_placeholders(col: Collector) -> int:
    """CALLS 가 가리키는데 노드가 없는 CodeUnit 을 missing-from-source placeholder 로 만든다 (빌드 직전에 호출)."""
    n = 0
    for (f, t, to), rec in list(col.edges.items()):
        if t == "CALLS" and rec.get("source") == SOURCE and to not in col.nodes and to.startswith("code:"):
            tail = to.split("#", 1)[1]
            cls, _, meth = tail.partition("::")
            col.node(node_rec(to, "CodeUnit", tail, SOURCE, props={"kind": "method", "lineStart": 0, "lineEnd": 0, "class": cls, "placeholder": True},
                              status="missing-from-source", source_ref=rec.get("sourceRef")))
            fuid = "file:" + to[len("code:"):].split("#", 1)[0]
            if fuid in col.nodes:
                col.edge(edge_rec(fuid, "CONTAINS", to, SOURCE, source_ref=rec.get("sourceRef")))
            n += 1
    return n


def _report(col: Collector, repo: str, s: _Stats) -> None:
    lines = col.sections["php"]
    lines += [f"### {repo}", "",
              f"- 파일 {s.files} · 클래스 {s.classes} · 코드 유닛 {s.units} · `->query(` {s.queries}건",
              f"- 테이블 자리를 못 찾은 쿼리: {len(s.zero_table)}건 (헬퍼가 조립하는 SQL·SHOW/DESCRIBE — tree-sitter 업그레이드 판단 자료)",
              f"- 테이블 이름은 있는데 전부 스키마에 없는 쿼리: {s.unknown_only}건 (폐기 테이블·결제 확장)",
              f"- 테이블 자리가 변수인 쿼리: {len(s.dynamic)}건",
              f"- 클래스는 있는데 메서드가 없어 placeholder 를 가리킨 호출: {s.placeholders}건",
              f"- 큐 발행 role 별 건수: {dict(s.queue_roles)}" + (f" · key 를 못 읽은 sendMessage: {len(s.no_key_publish)}건" if s.no_key_publish else ""), ""]
    if s.zero_table:
        lines += ["테이블 자리를 못 찾은 쿼리 (최대 40):", ""] + [f"- `{r}`" for r in s.zero_table[:40]] + [""]
    if s.dynamic:
        lines += ["동적 테이블명 (최대 20):", ""] + [f"- `{r}`" for r in s.dynamic[:20]] + [""]
    if s.unknown_table:
        lines += ["키워드 자리에 왔지만 스키마에 없는 이름 (상위 30):", ""] + [f"- `{k}`: {v}" for k, v in s.unknown_table.most_common(30)] + [""]
    if s.unknown_receiver:
        lines += ["`->query(` 인데 DB 핸들이 아닌 수신자 (건수):", ""] + [f"- `{k}`: {v}" for k, v in s.unknown_receiver.most_common(15)] + [""]
    if s.unresolved:
        lines += ["해석 못 한 load 대상 (상위 30):", ""] + [f"- `{k}`: {v}" for k, v in s.unresolved.most_common(30)] + [""]
