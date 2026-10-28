"""Laravel 추출기 — zoomzoom-auth (3단계, ZDV-347).

산출: Module(laravel-app)·File·CodeUnit(model/command/controller/class/method)·MAPS_TO(Eloquent `$table`)·READS/WRITES
(`DB::table`·`DB::select…`·Eloquent 정적 호출)·CronJob(Kernel 스케줄)+TRIGGERS·Route(http)+HANDLES·CALLS(di/static/self).
php.py 와 같은 규칙: SQL 텍스트는 테이블 토큰만 뽑고 버린다. config/·.env·storage·vendor 는 읽지 않는다.
테이블 이름은 Laravel 접두사(`DB_PREFIX`=zoom_) 를 붙여 스키마와 맞춘다. `mysql_without_prefix` 연결은 그대로.
CronJob uid 는 docs.py(scheduled-jobs.md) 와 합쳐지도록 `zzt-cron:` 네임스페이스를 뗀 짧은 이름을 쓴다.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import model, php, phplex, sqlshape
from .collect import Collector, edge_rec, node_rec
from .guard import is_denied_path
from .schema import Schema
from .sources import SERVICE

SOURCE = "laravel@1"
REPO = "zoomzoom-auth"
HOST = "sf"
AREAS = [("app", True), ("routes", True)]
SKIP_PREFIXES = ("config/", "storage/", "vendor/", "bootstrap/", "database/", "public/", "resources/", "tests/")
TABLE_PREFIX = "zoom_"
# routes/ 하위 디렉터리 → (URL 접두사, 컨트롤러 네임스페이스). 원본: app/Providers/RouteServiceProvider.php
ROUTE_DIRS = [
    ("routes/api/int/v1/", "int/v1", "App\\Http\\Controllers\\Int\\V1"),
    ("routes/api/v1/", "v1", "App\\Http\\Controllers\\V1"),
    ("routes/api/v2/", "v2", "App\\Http\\Controllers\\V2"),
    ("routes/admin/", "admin", "App\\Http\\Controllers\\Admin"),
    ("routes/web/", "", "App\\Http\\Controllers\\Web"),
]
HTTP_VERBS = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "delete": "DELETE", "any": "ANY", "options": "OPTIONS"}
ELOQUENT_READ = {"where", "whereIn", "whereNotIn", "whereNull", "whereNotNull", "whereBetween", "whereRaw", "whereHas", "whereDate",
                 "find", "findOrFail", "findMany", "first", "firstOrFail", "all", "get", "select", "selectRaw", "query", "count", "exists",
                 "pluck", "with", "orderBy", "orderByRaw", "join", "leftJoin", "has", "latest", "oldest", "distinct", "groupBy", "limit",
                 "skip", "take", "chunk", "cursor", "max", "min", "sum", "avg", "withTrashed", "onlyTrashed", "lockForUpdate", "sharedLock",
                 "paginate", "value", "firstWhere", "whereColumn", "orWhere", "from", "withCount", "search"}
ELOQUENT_WRITE = {"create": "insert", "insert": "insert", "insertGetId": "insert", "insertOrIgnore": "insert", "firstOrCreate": "insert",
                  "firstOrNew": "insert", "updateOrCreate": "update", "updateOrInsert": "update", "upsert": "insert", "destroy": "delete",
                  "truncate": "truncate", "forceCreate": "insert"}
CHAIN_WRITE = {"insert": "insert", "insertGetId": "insert", "update": "update", "delete": "delete", "forceDelete": "delete",
               "increment": "update", "decrement": "update", "truncate": "truncate", "upsert": "insert", "updateOrInsert": "update",
               "touch": "update", "restore": "update"}
DB_RAW_FUNCS = {"select": "select", "insert": "insert", "update": "update", "delete": "delete", "statement": None}


@dataclass
class LaravelRepo:
    name: str = REPO
    root: Path = SERVICE / REPO


@dataclass
class _ClassInfo:
    rel: str
    cdef: phplex.ClassDef
    fqcn: str
    table: str | None = None          # Eloquent `$table` (접두사 없음, 코드 그대로)
    connection: str | None = None
    fillable: list[str] = field(default_factory=list)
    signature: str | None = None
    uses: dict[str, str] = field(default_factory=dict)   # 짧은 이름 → FQCN (파일의 use 문)
    di: dict[str, str] = field(default_factory=dict)     # 생성자 주입 속성 → 타입 짧은 이름


@dataclass
class _Index:
    by_short: dict[str, _ClassInfo] = field(default_factory=dict)
    by_fqcn: dict[str, _ClassInfo] = field(default_factory=dict)
    by_signature: dict[str, _ClassInfo] = field(default_factory=dict)

    def resolve(self, name: str, uses: dict[str, str], namespace: str | None) -> _ClassInfo | None:
        """토큰에 나온 클래스 이름(짧은 이름·FQCN)을 색인에서 찾는다."""
        n = name.lstrip("\\")
        if "\\" in n:
            return self.by_fqcn.get(n)
        if n in uses:
            return self.by_fqcn.get(uses[n]) or self.by_short.get(uses[n].rsplit("\\", 1)[-1])
        if namespace and f"{namespace}\\{n}" in self.by_fqcn:
            return self.by_fqcn[f"{namespace}\\{n}"]
        return self.by_short.get(n)

    def has_method(self, info: _ClassInfo, method: str, depth: int = 0) -> _ClassInfo | None:
        if depth > 8:
            return None
        if any(m.name == method for m in info.cdef.methods):
            return info
        if info.cdef.parent:
            parent = self.resolve(info.cdef.parent, info.uses, None)
            if parent and parent is not info:
                return self.has_method(parent, method, depth + 1)
        return None


@dataclass
class _Stats:
    files: int = 0
    classes: int = 0
    units: int = 0
    models: int = 0
    models_with_table: int = 0
    models_without_table: list[str] = field(default_factory=list)
    model_table_missing: Counter = field(default_factory=Counter)
    fillable_missing: Counter = field(default_factory=Counter)
    commands: int = 0
    schedules: int = 0
    schedules_without_class: list[str] = field(default_factory=list)
    routes: int = 0
    routes_unresolved: list[str] = field(default_factory=list)
    unknown_table: Counter = field(default_factory=Counter)
    unresolved_model: Counter = field(default_factory=Counter)
    unresolved_call: Counter = field(default_factory=Counter)
    placeholders: int = 0
    queries: int = 0


_is = php._is


def _qualified_name(toks: list[phplex.Tok], i: int) -> tuple[str, int]:
    """toks[i] 부터 `A\\B\\C` 꼴을 읽어 (이름, 다음 인덱스)."""
    parts: list[str] = []
    j = i
    if j < len(toks) and _is(toks[j], "punct", "\\"):
        parts.append("\\")
        j += 1
    while j < len(toks) and toks[j].kind == "ident":
        parts.append(toks[j].text)
        j += 1
        if j < len(toks) and _is(toks[j], "punct", "\\"):
            parts.append("\\")
            j += 1
        else:
            break
    return "".join(parts), j


def _uses(toks: list[phplex.Tok]) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == "ident" and t.text == "use" and i + 1 < len(toks) and toks[i + 1].kind == "ident" \
                and not (i > 0 and _is(toks[i - 1], "punct", ")")):      # 클로저의 use (...) 제외
            name, j = _qualified_name(toks, i + 1)
            alias = name.rsplit("\\", 1)[-1]
            if j < len(toks) and toks[j].kind == "ident" and toks[j].text == "as" and j + 1 < len(toks):
                alias = toks[j + 1].text
                j += 2
            if name and not name.startswith("function"):
                out[alias] = name.lstrip("\\")
            i = j
            continue
        i += 1
    return out


def _class_tokens(toks: list[phplex.Tok], c: phplex.ClassDef) -> list[phplex.Tok]:
    return [t for t in toks if c.line_start <= t.line <= c.line_end]


def _class_props(toks: list[phplex.Tok], c: phplex.ClassDef) -> tuple[str | None, str | None, list[str], str | None]:
    """클래스 범위에서 `$table`·`$connection`·`$fillable`·`$signature` 를 읽는다 (메서드 안은 보지 않는다)."""
    method_ranges = [(m.line_start, m.line_end) for m in c.methods]
    table = connection = signature = None
    fillable: list[str] = []
    ct = [t for t in _class_tokens(toks, c) if not any(a <= t.line <= b for a, b in method_ranges)]
    for i, t in enumerate(ct):
        if t.kind != "var" or i + 2 >= len(ct) or not _is(ct[i + 1], "punct", "="):
            continue
        v = ct[i + 2]
        if t.text == "$table" and v.kind == "str":
            table = v.text
        elif t.text == "$connection" and v.kind == "str":
            connection = v.text
        elif t.text == "$signature" and v.kind == "str":
            signature = v.text
        elif t.text == "$fillable" and (_is(v, "punct", "[") or (v.kind == "ident" and v.text == "array")):
            k = i + 2 if _is(v, "punct", "[") else i + 3
            open_, close = ("[", "]") if _is(v, "punct", "[") else ("(", ")")
            end = php._match_close(ct, k, open_, close)
            fillable = [x.text for x in ct[k + 1:end] if x.kind == "str"]
    return table, connection, fillable, signature


def _ctor_param_types(toks: list[phplex.Tok], c: phplex.ClassDef) -> dict[str, str]:
    """생성자 파라미터 `Type $var` → {$var: Type}. 클래스 토큰에서 `function __construct (` 를 찾아 괄호 안을 읽는다."""
    ct = _class_tokens(toks, c)
    for i, t in enumerate(ct):
        if t.kind == "ident" and t.text == "__construct" and i + 1 < len(ct) and _is(ct[i + 1], "punct", "("):
            end = php._match_close(ct, i + 1, "(", ")")
            out: dict[str, str] = {}
            inner = ct[i + 2:end]
            for k, tk in enumerate(inner):
                if tk.kind == "var" and k > 0 and inner[k - 1].kind == "ident" and inner[k - 1].text not in ("public", "private", "protected", "readonly"):
                    out[tk.text] = inner[k - 1].text
            return out
    return {}


def _di_props(c: phplex.ClassDef, param_types: dict[str, str]) -> dict[str, str]:
    ctor = next((m for m in c.methods if m.name == "__construct"), None)
    if not ctor or not param_types:
        return {}
    out: dict[str, str] = {}
    for st in phplex.statements(ctor.body):
        if len(st) >= 5 and _is(st[0], "var", "$this") and _is(st[1], "punct", "->") and st[2].kind == "ident" \
                and _is(st[3], "punct", "=") and st[4].kind == "var" and st[4].text in param_types:
            out[st[2].text] = param_types[st[4].text]
    return out


# --- 추출 본체 ---------------------------------------------------------------------

def extract(col: Collector, repo: LaravelRepo | None = None, schema: Schema | None = None) -> dict[str, str]:
    schema = schema or Schema.load()
    spec = repo or LaravelRepo()
    col.sections.setdefault("laravel", [])
    if not spec.root.is_dir():
        col.warn(SOURCE, f"{spec.name}: repo not found at {spec.root}")
        return {}
    known_tables = {uid[len("table:"):] for uid in col.nodes if uid.startswith("table:") and "/" not in uid}
    stats = _Stats()
    parsed: list[tuple[str, list[phplex.Tok], phplex.FileStructure, int, str]] = []
    for rel, path in _iter_files(spec, schema):
        src = path.read_text(encoding="utf-8", errors="replace")
        toks = phplex.tokenize(src)
        parsed.append((rel, toks, phplex.parse(toks), src.count("\n") + 1, hashlib.sha1(src.encode("utf-8", "replace")).hexdigest()))
    stats.files = len(parsed)
    idx = _build_index(parsed)
    name = spec.name
    modules: set[str] = set()
    pending_targets: dict[str, str] = {}      # placeholder 후보 uid → sourceRef

    for rel, toks, fs, loc, sha1 in parsed:
        area = _area_of(rel)
        muid = f"module:{name}/{area}"
        if muid not in modules:
            modules.add(muid)
            col.node(node_rec(muid, "Module", area, SOURCE, props={"kind": "laravel-app", "repo": name, "path": area}, source_ref=f"{name}/{area}"))
            col.edge(edge_rec(model.repo_uid(name), "CONTAINS", muid, SOURCE, source_ref=f"{name}/{area}"))
        fuid = model.file_uid(name, rel)
        col.node(node_rec(fuid, "File", rel.rsplit("/", 1)[-1], SOURCE,
                          props={"repo": name, "path": rel, "lang": "php", "loc": loc, "sha1": sha1, "area": area}, source_ref=f"{name}/{rel}"))
        col.edge(edge_rec(muid, "CONTAINS", fuid, SOURCE, source_ref=f"{name}/{rel}"))
        if rel.startswith("routes/"):
            _routes(col, name, rel, toks, idx, stats, pending_targets)
            continue
        for c in fs.classes:
            info = idx.by_fqcn[_fqcn(fs.namespace, c.name)]
            stats.classes += 1
            kind = _kind_of(rel)
            cuid = model.code_uid(name, rel, c.name)
            props: dict = {"kind": kind, "lineStart": c.line_start, "lineEnd": c.line_end, "methodCount": len(c.methods)}
            if c.parent:
                props["parent"] = c.parent
            if fs.namespace:
                props["namespace"] = fs.namespace
            if kind == "model":
                stats.models += 1
                if info.table:
                    stats.models_with_table += 1
                    props["table"] = info.table
                    if info.connection:
                        props["connection"] = info.connection
                    tname = _resolve_table(info.table, info.connection, known_tables)
                    if tname:
                        col.edge(edge_rec(cuid, "MAPS_TO", model.table_uid(tname), SOURCE, props={"via": "eloquent-table"},
                                          source_ref=f"{name}/{rel}:{c.line_start}"))
                        if info.fillable:
                            cols = []
                            for f in info.fillable:
                                if model.col_uid(tname, f) in col.nodes:
                                    cols.append(f)
                                else:
                                    stats.fillable_missing[f"{tname}.{f}"] += 1
                            props["columns"] = cols
                    else:
                        stats.model_table_missing[info.table] += 1
                else:
                    stats.models_without_table.append(info.fqcn)
            if kind == "command":
                stats.commands += 1
                if info.signature:
                    props["signature"] = info.signature.split()[0]
                    props["signatureFull"] = info.signature
            col.node(node_rec(cuid, "CodeUnit", c.name, SOURCE, props=props, source_ref=f"{name}/{rel}:{c.line_start}-{c.line_end}"))
            col.edge(edge_rec(fuid, "CONTAINS", cuid, SOURCE, source_ref=f"{name}/{rel}:{c.line_start}"))
            stats.units += 1
            for m in c.methods:
                stats.units += 1
                uid = model.code_uid(name, rel, c.name, m.name)
                mprops = {"kind": "method", "lineStart": m.line_start, "lineEnd": m.line_end, "visibility": m.visibility, "class": c.name}
                if m.is_static:
                    mprops["isStatic"] = True
                col.node(node_rec(uid, "CodeUnit", f"{c.name}::{m.name}", SOURCE, props=mprops, source_ref=f"{name}/{rel}:{m.line_start}-{m.line_end}"))
                col.edge(edge_rec(fuid, "CONTAINS", uid, SOURCE, source_ref=f"{name}/{rel}:{m.line_start}"))
                if m.body:
                    _body(col, name, rel, info, m, uid, idx, known_tables, stats, pending_targets)
            if rel == "app/Console/Kernel.php" and c.name == "Kernel":
                _kernel(col, name, rel, c, idx, stats, pending_targets)

    for uid, ref in sorted(pending_targets.items()):
        if uid in col.nodes:
            continue
        tail = uid.split("#", 1)[1]
        cls, _, meth = tail.partition("::")
        col.node(node_rec(uid, "CodeUnit", tail, SOURCE, props={"kind": "method", "lineStart": 0, "lineEnd": 0, "class": cls, "placeholder": True},
                          status="missing-from-source", source_ref=ref))
        fuid = "file:" + uid[len("code:"):].split("#", 1)[0]
        if fuid in col.nodes:
            col.edge(edge_rec(fuid, "CONTAINS", uid, SOURCE, source_ref=ref))
        stats.placeholders += 1
    _report(col, name, stats)
    return {name: f"files={stats.files} classes={stats.classes} units={stats.units} models={stats.models} schedules={stats.schedules} routes={stats.routes}"}


def _iter_files(spec: LaravelRepo, schema: Schema) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for area, _ in AREAS:
        base = spec.root / area
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.php")):
            rel = p.relative_to(spec.root).as_posix()
            if rel.startswith(SKIP_PREFIXES) or is_denied_path(f"{spec.name}/{rel}", schema):
                continue
            out.append((rel, p))
    return out


def _area_of(rel: str) -> str:
    parts = rel.split("/")
    if parts[0] == "routes":
        return "routes"
    if len(parts) > 3 and parts[1] in ("Console", "Http"):
        return "/".join(parts[:3])
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def _kind_of(rel: str) -> str:
    if rel.startswith("app/Entities/") or rel.startswith("app/Models/"):
        return "model"
    if rel.startswith("app/Console/Commands/"):
        return "command"
    if rel.startswith("app/Http/Controllers/"):
        return "controller"
    return "class"


def _fqcn(namespace: str | None, cls: str) -> str:
    return f"{namespace}\\{cls}" if namespace else cls


def _build_index(parsed) -> _Index:
    idx = _Index()
    for rel, toks, fs, _, _ in parsed:
        uses = _uses(toks)
        for c in fs.classes:
            table, connection, fillable, signature = _class_props(toks, c)
            info = _ClassInfo(rel, c, _fqcn(fs.namespace, c.name), table, connection, fillable, signature, uses)
            info.di = _di_props(c, _ctor_param_types(toks, c))
            idx.by_fqcn.setdefault(info.fqcn, info)
            idx.by_short.setdefault(c.name, info)
            if signature:
                idx.by_signature.setdefault(signature.split()[0], info)
    return idx


def _resolve_table(raw: str, connection: str | None, known: set[str]) -> str | None:
    cands = [raw] if connection == "mysql_without_prefix" else [TABLE_PREFIX + raw, raw]
    return next((c for c in cands if c in known), None)


def _method_uid(name: str, idx: _Index, info: _ClassInfo, method: str, pending: dict[str, str], ref: str) -> str:
    owner = idx.has_method(info, method)
    if owner:
        return model.code_uid(name, owner.rel, owner.cdef.name, method)
    uid = model.code_uid(name, info.rel, info.cdef.name, method)
    pending.setdefault(uid, ref)
    return uid


# --- 메서드 몸통 ----------------------------------------------------------------------

def _body(col: Collector, name: str, rel: str, info: _ClassInfo, m: phplex.Method, uid: str, idx: _Index, known: set[str],
          stats: _Stats, pending: dict[str, str]) -> None:
    reads: dict[str, dict] = {}
    writes: dict[str, dict] = {}
    calls: dict[str, dict] = {}
    env: dict[str, str] = {}

    def add_table(raw: str | None, ops: set[str], line: int, handle: str, via_model: bool = False) -> None:
        if raw is None:
            return
        tname = _resolve_table(raw, info.connection if via_model else None, known)
        if tname is None:
            stats.unknown_table[raw] += 1
            return
        tuid = model.table_uid(tname)
        for op in ops:
            bucket = reads if op == "select" else writes
            e = bucket.setdefault(tuid, {"ops": set(), "lines": set(), "handles": set()})
            e["ops"].add(op)
            e["lines"].add(line)
            e["handles"].add(handle)

    def chain_write_ops(st: list[phplex.Tok], start: int) -> set[str]:
        ops: set[str] = set()
        for k in range(start, len(st) - 2):
            if _is(st[k], "punct", "->") and st[k + 1].kind == "ident" and _is(st[k + 2], "punct", "(") and st[k + 1].text in CHAIN_WRITE:
                ops.add(CHAIN_WRITE[st[k + 1].text])
        return ops

    for st in phplex.statements(m.body):
        n = len(st)
        if n >= 3 and st[0].kind == "var" and _is(st[1], "punct", "="):
            env[st[0].text] = php._eval(st[2:], env)
        elif n >= 3 and st[0].kind == "var" and _is(st[1], "punct", ".="):
            env[st[0].text] = env.get(st[0].text, " ? ") + php._eval(st[2:], env)
        i = 0
        while i < n:
            t = st[i]
            # DB::table('x') … / DB::select("…")
            if t.kind == "ident" and t.text == "DB" and i + 3 < n and _is(st[i + 1], "punct", "::") and st[i + 2].kind == "ident" and _is(st[i + 3], "punct", "("):
                fn = st[i + 2].text
                end = php._match_close(st, i + 3, "(", ")")
                args = php._split_args(st[i + 4:end])
                if fn == "table" and args and len(args[0]) == 1 and args[0][0].kind == "str":
                    stats.queries += 1
                    ops = chain_write_ops(st, end) or {"select"}
                    add_table(args[0][0].text.split()[0].strip("`"), ops, t.line, "db")      # 'order as o' → order
                elif fn in DB_RAW_FUNCS and args:
                    stats.queries += 1
                    sh = sqlshape.shape(php._eval(args[0], env))
                    for tbl, ops in sh.tables.items():
                        add_table(tbl[len(TABLE_PREFIX):] if tbl.startswith(TABLE_PREFIX) else tbl, ops, t.line, "db")
                i = end + 1
                continue
            # Class::method(
            if t.kind == "ident" and i + 3 < n and _is(st[i + 1], "punct", "::") and st[i + 2].kind == "ident" and _is(st[i + 3], "punct", "("):
                cls_name, meth = t.text, st[i + 2].text
                if cls_name in ("self", "static", "parent"):
                    target = idx.has_method(info, meth) if cls_name != "parent" else None
                    if cls_name == "parent" and info.cdef.parent:
                        parent = idx.resolve(info.cdef.parent, info.uses, None)
                        target = idx.has_method(parent, meth) if parent else None
                    if target:
                        tuid = model.code_uid(name, target.rel, target.cdef.name, meth)
                        calls.setdefault(tuid, {"kind": "self", "lines": set()})["lines"].add(t.line)
                elif cls_name not in ("DB", "Schema", "Route", "Log", "Cache", "Redis", "Mail", "Queue", "Storage", "Config", "Auth", "Hash", "Carbon", "Str", "Arr"):
                    target_info = idx.resolve(cls_name, info.uses, _ns_of(info.fqcn))
                    if target_info is None:
                        if meth in ELOQUENT_READ or meth in ELOQUENT_WRITE:
                            stats.unresolved_model[cls_name] += 1
                        else:
                            stats.unresolved_call[cls_name] += 1
                    elif target_info.table is None and _kind_of(target_info.rel) == "model" and (meth in ELOQUENT_READ or meth in ELOQUENT_WRITE):
                        stats.unresolved_model[f"{cls_name} (no $table)"] += 1
                    elif target_info.table is not None and (meth in ELOQUENT_READ or meth in ELOQUENT_WRITE):
                        stats.queries += 1
                        end = php._match_close(st, i + 3, "(", ")")
                        ops = chain_write_ops(st, end)
                        if meth in ELOQUENT_WRITE:
                            ops.add(ELOQUENT_WRITE[meth])
                        if not ops:
                            ops = {"select"}
                        tname = _resolve_table(target_info.table, target_info.connection, known)
                        if tname is None:
                            stats.unknown_table[target_info.table] += 1
                        else:
                            tuid = model.table_uid(tname)
                            for op in ops:
                                bucket = reads if op == "select" else writes
                                e = bucket.setdefault(tuid, {"ops": set(), "lines": set(), "handles": set()})
                                e["ops"].add(op)
                                e["lines"].add(t.line)
                                e["handles"].add("eloquent")
                    else:
                        tuid = _method_uid(name, idx, target_info, meth, pending, f"{name}/{rel}:{t.line}")
                        if tuid != uid:
                            calls.setdefault(tuid, {"kind": "static", "lines": set()})["lines"].add(t.line)
                i += 3
                continue
            # $this->x->m( / $this->m(
            if _is(t, "var", "$this") and i + 2 < n and _is(st[i + 1], "punct", "->") and st[i + 2].kind == "ident":
                a = st[i + 2].text
                if i + 5 < n and _is(st[i + 3], "punct", "->") and st[i + 4].kind == "ident" and _is(st[i + 5], "punct", "("):
                    tname_ = info.di.get(a)
                    if tname_:
                        target_info = idx.resolve(tname_, info.uses, _ns_of(info.fqcn))
                        if target_info:
                            tuid = _method_uid(name, idx, target_info, st[i + 4].text, pending, f"{name}/{rel}:{t.line}")
                            calls.setdefault(tuid, {"kind": "di", "lines": set()})["lines"].add(t.line)
                        else:
                            stats.unresolved_call[tname_] += 1
                    i += 5
                    continue
                if i + 3 < n and _is(st[i + 3], "punct", "("):
                    owner = idx.has_method(info, a)
                    if owner:
                        tuid = model.code_uid(name, owner.rel, owner.cdef.name, a)
                        if tuid != uid:
                            calls.setdefault(tuid, {"kind": "self", "lines": set()})["lines"].add(t.line)
                    i += 3
                    continue
            i += 1

    for bucket, etype in ((reads, "READS"), (writes, "WRITES")):
        for tuid, e in bucket.items():
            col.edge(edge_rec(uid, etype, tuid, SOURCE, props={"ops": sorted(e["ops"]), "lines": sorted(e["lines"]), "handle": ",".join(sorted(e["handles"]))},
                              source_ref=f"{name}/{rel}:{min(e['lines'])}"))
    for tuid, e in calls.items():
        col.edge(edge_rec(uid, "CALLS", tuid, SOURCE, props={"kind": e["kind"], "lines": sorted(e["lines"])}, source_ref=f"{name}/{rel}:{min(e['lines'])}"))


def _ns_of(fqcn: str) -> str | None:
    return fqcn.rsplit("\\", 1)[0] if "\\" in fqcn else None


# --- Kernel 스케줄 ------------------------------------------------------------------

def _kernel(col: Collector, name: str, rel: str, c: phplex.ClassDef, idx: _Index, stats: _Stats, pending: dict[str, str]) -> None:
    methods = {m.name: m for m in c.methods}
    sched = methods.get("schedule")
    if not sched:
        col.warn(SOURCE, f"{rel}: Kernel::schedule not found")
        return
    helpers: list[str] = ["schedule"]
    for st in phplex.statements(sched.body):
        for k in range(len(st) - 3):
            if _is(st[k], "var", "$this") and _is(st[k + 1], "punct", "->") and st[k + 2].kind == "ident" and _is(st[k + 3], "punct", "(") \
                    and st[k + 2].text in methods and st[k + 2].text not in helpers:
                helpers.append(st[k + 2].text)
    seen: set[str] = set()
    for h in helpers:
        flag: str | None = None
        for st in phplex.statements(methods[h].body):
            if st and st[0].kind == "ident" and st[0].text == "if":
                for k in range(len(st) - 2):
                    if _is(st[k], "ident", "config") and _is(st[k + 1], "punct", "(") and st[k + 2].kind == "str" and "cron" in st[k + 2].text:
                        flag = st[k + 2].text
                continue
            for k in range(len(st) - 4):
                if _is(st[k], "ident", "schedule") and _is(st[k + 1], "punct", "->") and _is(st[k + 2], "ident", "command") \
                        and _is(st[k + 3], "punct", "(") and st[k + 4].kind == "str":
                    sig_full = st[k + 4].text
                    sig = sig_full.split()[0]
                    end = php._match_close(st, k + 3, "(", ")")
                    chain = _chain_text(st, end + 1)
                    short = sig.split(":", 1)[1] if ":" in sig else sig
                    cuid = model.cron_uid(name, short)
                    if sig in seen:
                        continue          # dev 분기에서 같은 작업을 다시 등록한 것
                    seen.add(sig)
                    stats.schedules += 1
                    props = {"schedule": chain or "?", "host": HOST, "runner": "laravel-schedule", "kernelLine": st[k].line, "signature": sig}
                    if flag:
                        props["enabledFlag"] = flag
                    ref = f"{name}/{rel}:{st[k].line}"
                    info = idx.by_signature.get(sig)
                    if info:
                        target = _method_uid(name, idx, info, "handle", pending, ref)
                        props["target"] = target
                    else:
                        stats.schedules_without_class.append(sig)
                        target = None
                    col.node(node_rec(cuid, "CronJob", short, SOURCE, props=props, source_ref=ref))
                    if target:
                        col.edge(edge_rec(cuid, "TRIGGERS", target, SOURCE, props={"schedule": chain or "?"}, source_ref=ref))
                    break


def _chain_text(st: list[phplex.Tok], i: int) -> str:
    """`->timezone('Asia/Seoul')->dailyAt('04:50')` → `timezone(Asia/Seoul) dailyAt(04:50)`. 리터럴만 적는다."""
    parts: list[str] = []
    while i + 2 < len(st) and _is(st[i], "punct", "->") and st[i + 1].kind == "ident" and _is(st[i + 2], "punct", "("):
        end = php._match_close(st, i + 2, "(", ")")
        lits = [t.text for t in st[i + 3:end] if t.kind in ("str", "num")]
        parts.append(f"{st[i + 1].text}({','.join(lits)})")
        i = end + 1
    return " ".join(parts)


# --- 라우트 ---------------------------------------------------------------------------

def _routes(col: Collector, name: str, rel: str, toks: list[phplex.Tok], idx: _Index, stats: _Stats, pending: dict[str, str]) -> None:
    base_prefix, ns = "", "App\\Http\\Controllers"
    for d, pfx, n in ROUTE_DIRS:
        if rel.startswith(d):
            base_prefix, ns = pfx, n
            break
    _route_block(col, name, rel, toks, 0, len(toks), [base_prefix] if base_prefix else [], ns, idx, stats, pending)


def _route_block(col, name, rel, toks, start, end, prefixes, ns, idx, stats, pending) -> None:
    i = start
    while i < end:
        t = toks[i]
        if t.kind == "ident" and t.text == "Route" and i + 3 < end and _is(toks[i + 1], "punct", "::") and toks[i + 2].kind == "ident" and _is(toks[i + 3], "punct", "("):
            verb = toks[i + 2].text
            close = php._match_close(toks, i + 3, "(", ")")
            if verb in ("group", "prefix", "middleware", "name"):
                # Route::group([...], function () { ... })  /  Route::prefix('x')->group(function () { ... })
                extra = _array_prefix(toks[i + 4:close]) if verb == "group" else (toks[i + 4].text if verb == "prefix" and toks[i + 4].kind == "str" else None)
                body_open = next((k for k in range(i + 4, min(close + 40, end)) if _is(toks[k], "punct", "{")), None)
                if body_open is not None:
                    body_close = php._match_close(toks, body_open, "{", "}")
                    _route_block(col, name, rel, toks, body_open + 1, body_close, prefixes + ([extra] if extra else []), ns, idx, stats, pending)
                    i = max(body_close, close) + 1
                    continue
                i = close + 1
                continue
            if verb in HTTP_VERBS:
                args = php._split_args(toks[i + 4:close])
                if len(args) >= 2 and len(args[0]) == 1 and args[0][0].kind == "str":
                    path = "/" + "/".join(p.strip("/") for p in prefixes + [args[0][0].text] if p.strip("/"))
                    method = HTTP_VERBS[verb]
                    ruid = model.route_uid(name, method, path)
                    stats.routes += 1
                    col.node(node_rec(ruid, "Route", f"{method} {path}", SOURCE, props={"repo": name, "kind": "http", "method": method, "path": path, "file": rel},
                                      source_ref=f"{name}/{rel}:{t.line}"))
                    action = args[1]
                    handler = None
                    if len(action) == 1 and action[0].kind == "str" and "@" in action[0].text:
                        handler = tuple(action[0].text.split("@", 1))
                    elif len(action) >= 5 and _is(action[0], "punct", "[") and action[1].kind == "ident" and _is(action[2], "punct", "::") \
                            and _is(action[3], "ident", "class") and action[-2].kind == "str":
                        handler = (action[1].text, action[-2].text)
                    if handler:
                        cls, meth = handler
                        info = idx.by_fqcn.get(f"{ns}\\{cls}") or idx.by_fqcn.get(cls.lstrip("\\")) or idx.by_short.get(cls.rsplit("\\", 1)[-1])
                        if info:
                            cuid = _method_uid(name, idx, info, meth, pending, f"{name}/{rel}:{t.line}")
                            col.edge(edge_rec(cuid, "HANDLES", ruid, SOURCE, source_ref=f"{name}/{rel}:{t.line}"))
                        else:
                            stats.routes_unresolved.append(f"{rel}:{t.line} {cls}@{meth}")
                    else:
                        stats.routes_unresolved.append(f"{rel}:{t.line} (closure)")
                i = close + 1
                continue
        i += 1


def _array_prefix(arg: list[phplex.Tok]) -> str | None:
    for k in range(len(arg) - 2):
        if _is(arg[k], "str", "prefix") and _is(arg[k + 1], "punct", "=>") and arg[k + 2].kind == "str":
            return arg[k + 2].text
    return None


# --- report -----------------------------------------------------------------------------

def _report(col: Collector, name: str, s: _Stats) -> None:
    lines = col.sections["laravel"]
    lines += [f"### {name}", "",
              f"- 파일 {s.files} · 클래스 {s.classes} · 코드 유닛 {s.units} · DB 접근 지점 {s.queries}",
              f"- 모델 {s.models} (`$table` 있음 {s.models_with_table} · 없음 {len(s.models_without_table)}) · 명령 {s.commands} · 스케줄 {s.schedules} · 라우트 {s.routes}",
              f"- placeholder 로 만든 호출·핸들러 대상: {s.placeholders}건", ""]
    if s.models_without_table:
        lines += ["`$table` 이 없는 모델 (테이블을 추측하지 않음):", ""] + [f"- `{m}`" for m in sorted(s.models_without_table)] + [""]
    if s.model_table_missing:
        lines += ["모델 `$table` 이 스키마에 없음:", ""] + [f"- `{k}`: {v}" for k, v in s.model_table_missing.most_common(30)] + [""]
    if s.fillable_missing:
        lines += ["`$fillable` 에 있는데 스키마에 없는 컬럼 (상위 20):", ""] + [f"- `{k}`" for k, _ in s.fillable_missing.most_common(20)] + [""]
    if s.schedules_without_class:
        lines += ["스케줄은 있는데 명령 클래스가 없음:", ""] + [f"- `{x}`" for x in s.schedules_without_class] + [""]
    if s.unknown_table:
        lines += ["쿼리의 테이블 이름이 스키마에 없음 (상위 20):", ""] + [f"- `{k}`: {v}" for k, v in s.unknown_table.most_common(20)] + [""]
    if s.unresolved_model:
        lines += ["Eloquent 호출인데 모델 클래스를 못 찾음 (상위 20):", ""] + [f"- `{k}`: {v}" for k, v in s.unresolved_model.most_common(20)] + [""]
    if s.unresolved_call:
        lines += ["정적/DI 호출 대상 클래스를 못 찾음 (상위 20):", ""] + [f"- `{k}`: {v}" for k, v in s.unresolved_call.most_common(20)] + [""]
    if s.routes_unresolved:
        lines += [f"컨트롤러를 못 찾은 라우트 ({len(s.routes_unresolved)}건, 최대 20):", ""] + [f"- `{x}`" for x in s.routes_unresolved[:20]] + [""]
