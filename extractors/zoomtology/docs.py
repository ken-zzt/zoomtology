"""문서 허브(zoomzoom-services)에서 Doc·BusinessRule·EnumValue·CronJob·Repo 와 문서 근거 관계를 뽑는다.

읽는 것: docs/**/*.md 프론트매터(sources, last_verified), 20-database/status-codes.md, domains/*.md, policies/*.md,
30-operations/scheduled-jobs.md, 00-overview/glossary.md, 20-database/table-ownership.md, tools/repos.tsv.
문서 본문은 보관하지 않는다 — 제목·표의 값·경로만.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import yaml

from . import model
from .collect import Collector, edge_rec, node_rec
from .sources import HUB, HUB_REPO_NAME

SOURCE = "docs@1"
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
H1_RE = re.compile(r"^# (.+)$", re.M)
H3_RE = re.compile(r"^### (.+)$", re.M)
TICK_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
TABLE_COL_RE = re.compile(r"^`?([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)`?$")
CRON_RE = re.compile(r"^(\*|[\d,*/-]+)(\s+(\*|[\d,*/-]+)){4}$")
LANG_BY_EXT = {".php": "php", ".ts": "ts", ".tsx": "tsx", ".js": "js", ".tpl": "tpl", ".twig": "twig", ".sql": "sql",
               ".py": "py", ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".sh": "sh", ".md": "md", ".env": "env"}
PHP_REPOS = {"zoomzoom-admin", "zoomzoom-partners", "zoomzoom-auth"}


def doc_uid_for(path: Path, section: str | None = None) -> str:
    return model.doc_uid(HUB_REPO_NAME, path.relative_to(HUB).as_posix(), section)


def frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def md_tables(text: str) -> Iterable[tuple[int, list[str], list[list[str]]]]:
    """(시작 줄 번호, 헤더 셀, 행들) — 구분선 `|---|` 이 있는 표만."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith("|") and re.match(r"^\|\s*:?-{2,}", lines[i + 1]):
            header = _cells(lines[i])
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(_cells(lines[j]))
                j += 1
            yield i + 1, header, rows
            i = j
        else:
            i += 1


def _cells(line: str) -> list[str]:
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def _section_text(text: str, heading_pos: int) -> str:
    """heading 다음부터 다음 같은 레벨(###) 또는 상위(##) 헤딩 전까지."""
    rest = text[heading_pos:]
    rest = rest[rest.index("\n") + 1:] if "\n" in rest else ""
    m = re.search(r"^##+ ", rest, re.M)
    return rest[: m.start()] if m else rest


# --- 1. 모든 문서 → Doc 노드 + sources → DOCUMENTED_BY --------------------------

def extract_docs(col: Collector) -> int:
    count = 0
    for path in sorted((HUB / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        h1 = H1_RE.search(text)
        duid = doc_uid_for(path)
        props = {"type": fm.get("type", "unknown"), "status": fm.get("status"), "lastVerified": _s(fm.get("last_verified")),
                 "updated": _s(fm.get("updated")), "tags": list(fm.get("tags") or [])}
        if fm.get("audience"):
            props["audience"] = fm["audience"]
        col.node(node_rec(duid, "Doc", path.name, SOURCE, summary=h1.group(1).strip() if h1 else None, props=props,
                          source_ref=path.relative_to(HUB.parent).as_posix()))
        count += 1
        for src in fm.get("sources") or []:
            target = _source_target(col, str(src), path)
            if target:
                col.edge(edge_rec(target, "DOCUMENTED_BY", duid, SOURCE, source_ref=f"{path.relative_to(HUB.parent).as_posix()} frontmatter sources"))
    return count


def _source_target(col: Collector, src: str, doc_path: Path) -> str | None:
    """`Service/<repo>/<path>` → file:/module: uid (노드가 없으면 placeholder 생성). 허브 자신·비경로는 None."""
    s = src.strip()
    if not s.startswith("Service/"):
        return None
    parts = s[len("Service/"):].split("/")
    if len(parts) < 2:
        return None
    repo, rel = parts[0], "/".join(parts[1:])
    if repo == HUB_REPO_NAME:
        return None
    ext = Path(rel).suffix.lower()
    name = Path(rel).name
    if (ext and not rel.endswith("/")) or name in ("Dockerfile", "Makefile"):
        uid = model.file_uid(repo, rel)
        col.node(node_rec(uid, "File", name, SOURCE, props={"repo": repo, "path": rel, "lang": LANG_BY_EXT.get(ext, ext[1:] or name.lower())},
                          source_ref=f"{doc_path.relative_to(HUB.parent).as_posix()} sources"))
        return uid
    uid = f"module:{repo}/{rel.rstrip('/')}"
    col.node(node_rec(uid, "Module", rel.rstrip("/"), SOURCE,
                      props={"kind": "php-area" if repo in PHP_REPOS else "ts-dir", "repo": repo, "path": rel.rstrip("/")},
                      source_ref=f"{doc_path.relative_to(HUB.parent).as_posix()} sources"))
    return uid


def _s(v) -> str | None:
    return None if v is None else str(v)


# --- 2. status-codes.md → EnumValue ---------------------------------------------

def extract_status_codes(col: Collector) -> int:
    path = HUB / "docs" / "20-database" / "status-codes.md"
    if not path.exists():
        col.warn(SOURCE, "status-codes.md not found")
        return 0
    text = path.read_text(encoding="utf-8")
    doc = doc_uid_for(path)
    ref = path.relative_to(HUB.parent).as_posix()
    n = 0
    for h in H3_RE.finditer(text):
        heading = h.group(1)
        targets = [m for m in TICK_RE.findall(heading) if TABLE_COL_RE.match(m)]
        if not targets:
            continue
        section = _section_text(text, h.start())
        tables = list(md_tables(section))
        if not tables:
            col.warn(SOURCE, f"status-codes: no table under heading {heading!r}")
            continue
        _, header, rows = tables[0]
        hidx = {name: i for i, name in enumerate(header)}
        vi, mi, li = hidx.get("값"), hidx.get("의미"), hidx.get("라벨")
        for target in targets:
            table, column = TABLE_COL_RE.match(target).groups()
            if vi is None:
                if header and header[0].strip("`") == column:
                    vi, mi = 0, (mi if mi is not None else (2 if len(header) > 2 else 1))
                else:
                    col.warn(SOURCE, f"status-codes: table under {heading!r} has no 값 column")
                    break
            cuid = model.col_uid(table, column)
            anchor = f"{table}.{column}"
            col.edge(edge_rec(cuid, "DOCUMENTED_BY", model.doc_uid(HUB_REPO_NAME, path.relative_to(HUB).as_posix(), anchor), SOURCE,
                              props={"section": heading}, source_ref=f"{ref}#{anchor}"))
            for row in rows:
                if len(row) <= vi:
                    continue
                value = _clean_value(row[vi])
                if value is None:
                    continue
                meaning = _clean_cell(row[mi]) if mi is not None and len(row) > mi else None
                label = _clean_cell(row[li]) if li is not None and len(row) > li else None
                euid = model.enum_uid(table, column, value)
                props = {"value": value, "origin": "status-codes"}
                if meaning:
                    props["meaning"] = meaning
                if label:
                    props["label"] = label
                col.node(node_rec(euid, "EnumValue", value, f"doc:{ref}", summary=meaning or label,
                                  props=props, source_ref=f"{ref}#{anchor}"))
                col.edge(edge_rec(cuid, "HAS_VALUE", euid, f"doc:{ref}", source_ref=f"{ref}#{anchor}"))
                n += 1
    # 섹션 헤딩 하나를 Doc 노드로 (근거 링크용)
    for h in H3_RE.finditer(text):
        for m in TICK_RE.findall(h.group(1)):
            mm = TABLE_COL_RE.match(m)
            if mm:
                anchor = f"{mm.group(1)}.{mm.group(2)}"
                col.node(node_rec(model.doc_uid(HUB_REPO_NAME, path.relative_to(HUB).as_posix(), anchor), "Doc",
                                  f"status-codes.md#{anchor}", SOURCE, summary=h.group(1), props={"type": "database", "section": True},
                                  source_ref=f"{ref}#{anchor}"))
    return n


def _clean_value(cell: str) -> str | None:
    v = cell.strip().strip("`").strip()
    if not v or v.startswith("~~"):
        return None
    v = v.split(" ")[0] if re.match(r"^-?\d+\s", v) else v
    return v if re.match(r"^[A-Za-z0-9_.-]+$", v) else None


LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def _clean_cell(cell: str) -> str | None:
    v = LINK_RE.sub(r"\1", BOLD_RE.sub(r"\1", cell)).replace("`", "").strip()
    return v or None


# --- 3. domains/*.md → Column.meaning, Table DOCUMENTED_BY --------------------------

def extract_domains(col: Collector) -> int:
    n = 0
    for path in sorted((HUB / "docs" / "20-database" / "domains").glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        ref = path.relative_to(HUB.parent).as_posix()
        for h in H3_RE.finditer(text):
            heading = h.group(1).strip().strip("`")
            if not re.match(r"^[A-Za-z0-9_]+$", heading):
                continue
            table = heading
            section = _section_text(text, h.start())
            col.node(node_rec(model.doc_uid(HUB_REPO_NAME, path.relative_to(HUB).as_posix(), table), "Doc",
                              f"{path.name}#{table}", SOURCE, summary=f"{path.stem}: {table}", props={"type": "database", "section": True},
                              source_ref=f"{ref}#{table}"))
            col.edge(edge_rec(model.table_uid(table), "DOCUMENTED_BY",
                              model.doc_uid(HUB_REPO_NAME, path.relative_to(HUB).as_posix(), table), SOURCE,
                              props={"section": table}, source_ref=f"{ref}#{table}"))
            for _, header, rows in md_tables(section):
                if not header or header[0] != "컬럼":
                    continue
                for row in rows:
                    if len(row) < 2:
                        continue
                    meaning = _clean_cell(row[1])
                    for cname in TICK_RE.findall(row[0]):
                        if not re.match(r"^[A-Za-z0-9_]+$", cname):
                            continue
                        props = {}
                        if meaning:
                            props["meaning"] = meaning
                        if "개인정보" in row[1]:
                            props["piiDoc"] = True
                        col.node(node_rec(model.col_uid(table, cname), "Column", cname, f"doc:{ref}", props=props,
                                          source_ref=f"{ref}#{table}"), partial=True)
                        n += 1
    return n


# --- 4. policies/*.md → BusinessRule + IMPLEMENTS_RULE --------------------------------

def extract_policies(col: Collector) -> int:
    n = 0
    for path in sorted((HUB / "docs" / "20-database" / "policies").glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        h1 = H1_RE.search(text)
        ref = path.relative_to(HUB.parent).as_posix()
        ruid = model.rule_uid(path.stem)
        title = h1.group(1).strip() if h1 else path.stem
        col.node(node_rec(ruid, "BusinessRule", title, SOURCE, summary=_first_paragraph(text),
                          props={"title": title, "doc": path.relative_to(HUB).as_posix(), "status": fm.get("status"),
                                 "lastVerified": _s(fm.get("last_verified")), "tags": list(fm.get("tags") or [])},
                          source_ref=ref))
        col.edge(edge_rec(ruid, "DOCUMENTED_BY", doc_uid_for(path), SOURCE, source_ref=ref))
        for src in fm.get("sources") or []:
            target = _source_target(col, str(src), path)
            if target:
                col.edge(edge_rec(target, "IMPLEMENTS_RULE", ruid, SOURCE, source_ref=f"{ref} frontmatter sources"))
        n += 1
    return n


def _first_paragraph(text: str) -> str | None:
    body = FM_RE.sub("", text, count=1)
    for block in body.split("\n\n"):
        b = block.strip()
        if not b or b.startswith(("#", ">", "|", "-", "```")):
            continue
        b = re.sub(r"\s+", " ", BOLD_RE.sub(r"\1", b))
        return b[:300]
    return None


# --- 5. scheduled-jobs.md → CronJob + TRIGGERS ----------------------------------------

def extract_cron(col: Collector) -> int:
    path = HUB / "docs" / "30-operations" / "scheduled-jobs.md"
    if not path.exists():
        col.warn(SOURCE, "scheduled-jobs.md not found")
        return 0
    text = path.read_text(encoding="utf-8")
    ref = path.relative_to(HUB.parent).as_posix()
    n = 0
    for line_no, header, rows in md_tables(text):
        if len(header) >= 4 and header[1].startswith("cron") and header[0] == "KST":
            # 1장 Admin / 2장 MQ
            is_mq = header[2] == "대상"
            for row in rows:
                if len(row) < 4 or row[0].startswith("~~") or row[2].startswith("~~"):
                    continue
                schedule = row[1].strip("` ")
                if not CRON_RE.match(schedule):
                    continue
                target_cell = row[2]
                summary = _clean_cell(row[3])
                if is_mq:
                    n += _mq_row(col, target_cell, schedule, summary, f"{ref}:{line_no}")
                else:
                    n += _admin_row(col, target_cell, schedule, summary, f"{ref}:{line_no}")
        elif len(header) >= 4 and header[0] == "작업" and header[2] == "경로":
            # 3장 zoomzoom-auth Laravel
            for row in rows:
                if len(row) < 4:
                    continue
                names = TICK_RE.findall(row[0])
                if not names:
                    continue
                name = names[0]
                schedule = _clean_cell(row[1]) or "?"
                route_cell = row[2]
                summary = _clean_cell(row[3])
                cuid = model.cron_uid("zoomzoom-auth", name)
                col.node(node_rec(cuid, "CronJob", name, SOURCE, summary=summary,
                                  props={"schedule": schedule, "host": "sf", "runner": "laravel-schedule", "pathCell": _clean_cell(route_cell)},
                                  source_ref=f"{ref}:{line_no}"))
                col.edge(edge_rec(cuid, "DOCUMENTED_BY", doc_uid_for(path), SOURCE, source_ref=f"{ref}:{line_no}"))
                m = re.search(r"`(GET|POST|PUT|PATCH|DELETE)\s+([^`]+)`", route_cell)
                if m:
                    route = model.route_uid("zoomzoom-api", m.group(1), "/" + m.group(2).strip("/"))
                    _ensure_route(col, "zoomzoom-api", m.group(1), "/" + m.group(2).strip("/"), f"{ref}:{line_no}", kind="task")
                    col.edge(edge_rec(cuid, "TRIGGERS", route, SOURCE, props={"schedule": schedule, "via": "sqs→message-consumer→zoomzoom-back"},
                                      source_ref=f"{ref}:{line_no}"))
                n += 1
    return n


def _admin_row(col: Collector, cell: str, schedule: str, summary: str | None, ref: str) -> int:
    ep = TICK_RE.findall(cell)
    if not ep:
        return 0
    endpoint = ep[0].split("&")[0].strip("/")
    cuid = model.cron_uid("admin", endpoint.lower())      # OpenCart 라우트는 대소문자 무관 → 라우트 uid 와 같이 소문자
    col.node(node_rec(cuid, "CronJob", endpoint.split("/")[-1], SOURCE, summary=summary,
                      props={"schedule": schedule, "host": "admin", "runner": "crontab-curl", "endpoint": ep[0]}, source_ref=ref))
    ruid = model.opencart_route_uid("zoomzoom-admin", endpoint)
    col.node(node_rec(ruid, "Route", endpoint, SOURCE, props={"repo": "zoomzoom-admin", "kind": "opencart", "path": endpoint,
                      "area": "admin" if endpoint.startswith("cron/") else "catalog"}, source_ref=ref))
    col.edge(edge_rec(cuid, "TRIGGERS", ruid, SOURCE, props={"schedule": schedule}, source_ref=ref))
    return 1


def _mq_row(col: Collector, cell: str, schedule: str, summary: str | None, ref: str) -> int:
    m = re.search(r"`(GET|POST|PUT|PATCH|DELETE)\s+localhost:(\d+)(/[^`\s]*)`", cell)
    if m:
        method, port, path = m.group(1), m.group(2), m.group(3)
        repo = {"4000": "zoomzoom-api", "5000": "data-api"}.get(port)
        if not repo:
            col.warn(SOURCE, f"scheduled-jobs MQ row: unknown port {port} ({ref})")
            return 0
        rpath = re.sub(r"^/api/v1", "", path) or "/"
        target = f"{repo}/{rpath.strip('/')}"
        cuid = model.cron_uid("mq", rpath.strip("/"))
        col.node(node_rec(cuid, "CronJob", rpath.strip("/"), SOURCE, summary=summary,
                          props={"schedule": schedule, "host": "mq", "runner": "crontab-curl", "endpoint": f"{method} :{port}{path}"}, source_ref=ref))
        _ensure_route(col, repo, method, rpath, ref, kind="task")
        col.edge(edge_rec(cuid, "TRIGGERS", model.route_uid(repo, method, rpath), SOURCE, props={"schedule": schedule}, source_ref=ref))
        return 1
    ep = [e for e in TICK_RE.findall(cell) if "/" in e and " " not in e]
    if ep:
        endpoint = ep[0].strip("/")
        cuid = model.cron_uid("mq", endpoint.lower())
        col.node(node_rec(cuid, "CronJob", endpoint.split("/")[-1], SOURCE, summary=summary,
                          props={"schedule": schedule, "host": "mq", "runner": "crontab-curl", "endpoint": ep[0]}, source_ref=ref))
        ruid = model.opencart_route_uid("zoomzoom-admin", endpoint)
        col.node(node_rec(ruid, "Route", endpoint, SOURCE, props={"repo": "zoomzoom-admin", "kind": "opencart", "path": endpoint, "area": "catalog"}, source_ref=ref))
        col.edge(edge_rec(cuid, "TRIGGERS", ruid, SOURCE, props={"schedule": schedule}, source_ref=ref))
        return 1
    return 0


def _ensure_route(col: Collector, repo: str, method: str, path: str, ref: str, kind: str = "http") -> None:
    col.node(node_rec(model.route_uid(repo, method, path), "Route", f"{method} {path}", SOURCE,
                      props={"repo": repo, "kind": kind, "method": method, "path": path}, source_ref=ref))


# --- 6. glossary → Table.aliases, table-ownership → usageByRepo, repos.tsv → Repo ----------

def extract_glossary(col: Collector) -> int:
    path = HUB / "docs" / "00-overview" / "glossary.md"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    ref = path.relative_to(HUB.parent).as_posix()
    n = 0
    for _, header, rows in md_tables(text):
        for row in rows:
            if len(row) < 2:
                continue
            tables = re.findall(r"테이블 `([a-z][a-z0-9_]+)`", row[1])
            lead = re.match(r"^`([a-z][a-z0-9_]+)`", row[1])
            if lead:
                tables.append(lead.group(1))
            terms = [BOLD_RE.sub(r"\1", b) for b in BOLD_RE.findall(row[0])]
            terms = [re.sub(r"\s*\(.*?\)\s*", " ", t).strip() for t in terms]
            if header and header[0] == "테이블":
                tick = TICK_RE.findall(row[0])
                if tick and re.match(r"^[a-z][a-z0-9_]+$", tick[0]):
                    col.node(node_rec(model.table_uid(tick[0]), "Table", tick[0], f"doc:{ref}", summary=_clean_cell(row[1]),
                                      props={}, source_ref=ref), partial=True)
                    n += 1
                continue
            if terms and tables:
                aliases = []
                for t in terms:
                    aliases += [a.strip() for a in re.split(r"[/,]", t) if a.strip()]
                for table in tables:
                    col.node(node_rec(model.table_uid(table), "Table", table, f"doc:{ref}", props={"aliases": aliases}, source_ref=ref), partial=True)
                    n += 1
    return n


def extract_ownership(col: Collector) -> int:
    path = HUB / "docs" / "20-database" / "table-ownership.md"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    ref = path.relative_to(HUB.parent).as_posix()
    n = 0
    for _, header, rows in md_tables(text):
        if not header or header[0] != "테이블":
            continue
        repos = header[1:]
        for row in rows:
            tick = TICK_RE.findall(row[0])
            if not tick:
                continue
            usage = {}
            for repo, cell in zip(repos, row[1:]):
                c = cell.strip().split(" ")[0]
                if c.isdigit():
                    usage[repo] = int(c)
            col.node(node_rec(model.table_uid(tick[0]), "Table", tick[0], f"doc:{ref}", props={"usageByRepo": usage}, source_ref=ref), partial=True)
            n += 1
    return n


def extract_repos(col: Collector) -> int:
    path = HUB / "tools" / "repos.tsv"
    if not path.exists():
        col.warn(SOURCE, "repos.tsv not found")
        return 0
    ref = path.relative_to(HUB.parent).as_posix()
    n = 0
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("#name"):
            header = line[1:].split("\t")
            continue
        if line.startswith("#") or header is None:
            continue
        rec = dict(zip(header, line.split("\t")))
        name = rec["name"]
        props = {"stack": rec.get("stack"), "tier": rec.get("tier"), "status": rec.get("status"), "remote": rec.get("remote"),
                 "defaultBranch": rec.get("branch"), "deploy": rec.get("deploy"), "port": rec.get("port"), "process": rec.get("process")}
        col.node(node_rec(model.repo_uid(name), "Repo", name, SOURCE, summary=rec.get("stack"), props=props, source_ref=ref))
        n += 1
    return n


def extract(col: Collector) -> dict[str, str]:
    return {
        "docs": str(extract_docs(col)),
        "statusCodeValues": str(extract_status_codes(col)),
        "domainColumns": str(extract_domains(col)),
        "policies": str(extract_policies(col)),
        "cronJobs": str(extract_cron(col)),
        "glossary": str(extract_glossary(col)),
        "ownership": str(extract_ownership(col)),
        "repos": str(extract_repos(col)),
    }
