"""NestJS 계열 추출(3단계, ZDV-347) — `extractors/ts`(ts-morph, node) 가 저장소별 JSONL 을 만들고, 여기서 병합·검증·저장소 간 해석을 한다.

- 저장소: zoomzoom-api · message-consumer · zoomzoom-back · external-api · data-api · zoomzoom-front
- 저장소 간: message-consumer/front 의 raw CALLS_HTTP(`route:zoomzoom-back <M> /zoomzoom/<path>` placeholder) → back 의 AccessRule Route 로 재연결,
  AccessRule Route → zoomzoom-api Route(CALLS_HTTP, matchKind exact|target|regex), Service 노드(`svc:message-consumer/<role>`, `svc:zoomzoom-api/{prod-back,mq}`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import model
from .collect import Collector, edge_rec, node_rec
from .schema import Schema
from .sources import INPUTS, SERVICE, ZOOMTOLOGY

SOURCE = "ts@1"
TS_DIR = ZOOMTOLOGY / "extractors" / "ts"
REPOS = ["zoomzoom-api", "message-consumer", "zoomzoom-back", "external-api", "data-api", "zoomzoom-front"]
CONSUMER_ROLES = ["order", "email", "notif", "entity", "event"]
CONSUMER_PORT = {"order": 6000, "email": 6001, "notif": 6002, "entity": 6003, "event": 6004}
BACK_SERVICES = ("zoomzoom", "partner", "admin", "external", "document", "operation")


@dataclass
class TsRepo:
    name: str
    root: Path
    jsonl: Path | None = None       # 미리 만든 JSONL (테스트·캐시)


@dataclass
class _Stats:
    repos: dict[str, dict] = field(default_factory=dict)
    unknown_table: Counter = field(default_factory=Counter)
    dropped_rw: int = 0
    http_resolved: Counter = field(default_factory=Counter)
    http_unresolved: list[str] = field(default_factory=list)
    rule_to_api: Counter = field(default_factory=Counter)
    rule_unmatched: list[str] = field(default_factory=list)


def default_repos() -> list[TsRepo]:
    return [TsRepo(name, SERVICE / name) for name in REPOS]


def run_node(repo: TsRepo, out_dir: Path) -> Path | None:
    """node 추출기를 돌려 JSONL 을 만든다. ZOOMTOLOGY_TS_CACHE=1 이면 있는 파일을 재사용한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{repo.name}.jsonl"
    if os.environ.get("ZOOMTOLOGY_TS_CACHE") == "1" and out.exists():
        return out
    node = shutil.which("node")
    if not node:
        return None
    subprocess.run([node, str(TS_DIR / "src" / "extract.mjs"), repo.name, str(repo.root), str(out)], check=True, capture_output=True, text=True)
    return out


def load_jsonl(path: Path) -> tuple[list[dict], list[dict], dict]:
    nodes, edges, report = [], [], {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            kind = rec.pop("kind")
            if kind == "node":
                nodes.append(rec)
            elif kind == "edge":
                edges.append(rec)
            else:
                report = rec
    return nodes, edges, report


def extract(col: Collector, repos: list[TsRepo] | None = None, schema: Schema | None = None, out_dir: Path | None = None) -> dict[str, str]:
    repos = repos if repos is not None else default_repos()
    out_dir = out_dir or (INPUTS / "ts")
    stats = _Stats()
    meta: dict[str, str] = {}
    known_tables = {uid for uid in col.nodes if uid.startswith("table:")}
    raw_http: list[dict] = []      # CALLS_HTTP placeholder 들 (저장소 간 해석 대상)

    for repo in repos:
        if not repo.root.is_dir() and not repo.jsonl:
            col.warn(SOURCE, f"{repo.name}: repo not found at {repo.root}")
            continue
        path = repo.jsonl or run_node(repo, out_dir)
        if path is None:
            col.warn(SOURCE, f"{repo.name}: node not found — ts extractor skipped")
            meta[repo.name] = "skipped"
            continue
        nodes, edges, report = load_jsonl(path)
        rep = report.get("report", {})
        stats.repos[repo.name] = rep
        meta[repo.name] = f"files={rep.get('files', 0)} nodes={len(nodes)} edges={len(edges)} ms={report.get('ms', '?')}"
        for n in nodes:
            n.setdefault("props", {})
            n.setdefault("firstSeenAt", None)
            n.setdefault("lastSeenAt", None)
            n.setdefault("lastVerifiedAt", None)
            if n["label"] == "Route" and n["props"].get("placeholder"):
                continue                        # raw HTTP 대상 — 해석 뒤에 필요한 것만 만든다
            col.node(n)
        for e in edges:
            e.setdefault("props", {})
            e.setdefault("firstSeenAt", None)
            e.setdefault("lastSeenAt", None)
            e.setdefault("lastVerifiedAt", None)
            if e["type"] in ("READS", "WRITES", "MAPS_TO") and e["to"].startswith("table:"):
                if e["to"] not in known_tables:
                    stats.unknown_table[e["to"]] += 1
                    stats.dropped_rw += 1
                    continue
            if e["type"] == "CALLS_HTTP" and e["props"].get("raw"):
                raw_http.append(e)
                continue
            col.edge(e)

    _resolve_http(col, raw_http, stats)
    _rules_to_api(col, stats)
    _services(col)
    _report(col, stats)
    return meta


# --- 저장소 간 해석 ---------------------------------------------------------------------

_RULE_CACHE_KEY = "_ts_rules"


def _back_rules(col: Collector) -> dict[tuple[str, str], list[tuple[str, re.Pattern, dict]]]:
    """(service, METHOD) → [(route uid, compiled regex, props)]"""
    rules: dict[tuple[str, str], list] = {}
    for uid, n in col.nodes.items():
        if n["label"] != "Route" or n["props"].get("kind") != "accessrule":
            continue
        p = n["props"]
        try:
            rx = re.compile(p["path"])
        except re.error:
            continue
        rules.setdefault((p.get("service"), p.get("method")), []).append((uid, rx, p))
    return rules


def _resolve_http(col: Collector, raw: list[dict], stats: _Stats) -> None:
    rules = _back_rules(col)
    for e in raw:
        method, path = e["props"].get("method"), e["props"].get("path", "")
        target_repo = e["to"].split(" ", 1)[0][len("route:"):]
        if target_repo != "zoomzoom-back":
            # zoomzoom-auth 등 — 대상 라우트가 있으면 연결, 없으면 placeholder 유지
            _placeholder_or_link(col, e, stats)
            continue
        seg = path.strip("/").split("/", 1)
        service = seg[0] if seg and seg[0] in BACK_SERVICES else None
        url = seg[1] if len(seg) > 1 else ""
        if service == "external":
            # back 의 ExternalService 는 EXTERNAL_API_URL/<url> 로 그대로 넘기는 프록시 — external-api 라우트에 직접 잇는다
            target = _find_route(col, "external-api", method, "/" + url)
            if target:
                e2 = dict(e)
                e2["to"] = target
                e2["props"] = {k: v for k, v in e["props"].items() if k != "raw"} | {"via": "back-proxy", "service": service}
                col.edge(e2)
                stats.http_resolved["external-api"] += 1
                continue
        hit = None
        methods = [method] if method != "ANY" else ["GET", "POST", "PUT", "PATCH", "DELETE"]
        variants = _param_variants(url)
        for m in methods:
            for ruid, rx, _ in rules.get((service, m), []):
                if any(rx.search(v) for v in variants):
                    hit = ruid
                    break
            if hit:
                break
        if hit:
            e2 = dict(e)
            e2["to"] = hit
            e2["props"] = {k: v for k, v in e["props"].items() if k != "raw"} | {"via": "accessrule", "service": service}
            col.edge(e2)
            stats.http_resolved[e["from"].split("/", 1)[0][len("code:"):]] += 1
        else:
            _placeholder_or_link(col, e, stats)


def _placeholder_or_link(col: Collector, e: dict, stats: _Stats) -> None:
    ruid = e["to"]
    if ruid in col.nodes:
        e2 = dict(e)
        e2["props"] = {k: v for k, v in e["props"].items() if k != "raw"}
        col.edge(e2)
        stats.http_resolved["direct"] += 1
        return
    repo = ruid.split(" ", 1)[0][len("route:"):]
    method, path = e["props"].get("method"), e["props"].get("path", "")
    col.node(node_rec(ruid, "Route", f"{method} {path}", SOURCE, props={"repo": repo, "kind": "http", "method": method, "path": path, "placeholder": True},
                      status="missing-from-source", source_ref=e.get("sourceRef")))
    e2 = dict(e)
    e2["props"] = {k: v for k, v in e["props"].items() if k != "raw"}
    col.edge(e2)
    stats.http_unresolved.append(f"{method} {path} ← {e.get('sourceRef')}")


def _rules_to_api(col: Collector, stats: _Stats) -> None:
    """AccessRule Route → zoomzoom-api Route. target 이 있으면 그 경로, 아니면 정규식을 api 경로(파라미터는 숫자/문자로 치환)에 적용."""
    api_routes: dict[str, list[tuple[str, str, dict]]] = {}
    for uid, n in col.nodes.items():
        if n["label"] == "Route" and n["props"].get("repo") == "zoomzoom-api" and n["props"].get("kind") in ("http", "task"):
            api_routes.setdefault(n["props"].get("method", ""), []).append((uid, n["props"].get("path", ""), n["props"]))
    for uid, n in list(col.nodes.items()):
        if n["label"] != "Route" or n["props"].get("kind") != "accessrule":
            continue
        p = n["props"]
        method = p.get("method")
        candidates = api_routes.get(method, [])
        hits: list[tuple[str, str]] = []
        target = p.get("target")
        if target:
            tpath = "/" + target.strip("/").split("?", 1)[0]
            tnorm = re.sub(r"/(\d+)(?=/|$)", "/:p", tpath)
            for auid, apath, _ in candidates:
                if _same_path(apath, tpath) or _same_path(apath, tnorm):
                    hits.append((auid, "target"))
        else:
            try:
                rx = re.compile(p["path"])
            except re.error:
                rx = None
            if rx:
                for auid, apath, _ in candidates:
                    if any(rx.search(v) for v in _param_variants(apath.lstrip("/"))):
                        hits.append((auid, p.get("matchKind", "regex")))
        if not hits:
            stats.rule_unmatched.append(uid)
            continue
        if len(hits) > 12:
            hits = hits[:12]
            n["props"]["apiMatchTruncated"] = True
        for auid, kind in hits:
            col.edge(edge_rec(uid, "CALLS_HTTP", auid, SOURCE, props={"matchKind": kind, "method": method}, source_ref=n.get("sourceRef")))
            stats.rule_to_api[kind] += 1


def _find_route(col: Collector, repo: str, method: str, path: str) -> str | None:
    methods = [method] if method != "ANY" else ["GET", "POST", "PUT", "PATCH", "DELETE"]
    for uid, n in col.nodes.items():
        if n["label"] == "Route" and n["props"].get("repo") == repo and n["props"].get("method") in methods and n["props"].get("kind") in ("http", "task") \
                and not n["props"].get("placeholder") and _same_path(n["props"].get("path", ""), path):
            return uid
    return None


def _param_variants(path: str) -> set[str]:
    """`order/:id/confirm`·`order/:param/confirm` 의 파라미터 자리를 숫자·문자·`me`(back 이 세션 고객 id 로 바꾸는 자리)로 바꾼 후보들."""
    out = {path}
    for sub in ("1", "abc", "abc-1", "me"):
        out.add(re.sub(r":[A-Za-z0-9_]+", sub, path))
    return out


def _same_path(a: str, b: str) -> bool:
    """`/order/:id/rejected` 와 `/order/:p/rejected` 또는 `/order/123/rejected` 를 같은 경로로 본다."""
    sa, sb = a.strip("/").split("/"), b.strip("/").split("/")
    if len(sa) != len(sb):
        return False
    for x, y in zip(sa, sb):
        if x == y:
            continue
        if x.startswith(":") or y.startswith(":"):
            continue
        return False
    return True


def _services(col: Collector) -> None:
    if "repo:message-consumer" in col.nodes:
        for role in CONSUMER_ROLES:
            suid = model.service_uid("message-consumer", role)
            col.node(node_rec(suid, "Service", f"{role}-message-consumer", SOURCE,
                              summary=f"message-consumer 의 {role} 역할 프로세스 — SQS 큐 `{role}` 만 읽는다",
                              props={"repo": "message-consumer", "process": f"{role}-message-consumer", "port": CONSUMER_PORT[role], "host": "prod-back", "queue": role},
                              source_ref="zoomzoom-services/docs/10-services/message-consumer.md"))
            q = col.nodes.get(model.queue_uid(role))
            if q is not None:
                q["props"]["consumerService"] = suid
    if "repo:zoomzoom-api" in col.nodes:
        col.node(node_rec(model.service_uid("zoomzoom-api", "prod-back"), "Service", "zoomzoom-api (prod-back)", SOURCE,
                          summary="zoomzoom-api 운영 인스턴스 (prod-back-LA·SF, :4000)",
                          props={"repo": "zoomzoom-api", "process": "pm2 zoomzoom-api", "port": 4000, "host": "prod-back"},
                          source_ref="zoomzoom-services/tools/repos.tsv"))
        col.node(node_rec(model.service_uid("zoomzoom-api", "mq"), "Service", "zoomzoom-api (MQ 사본)", SOURCE,
                          summary="EC2 Live MQ 안의 zoomzoom-api 사본(:4000). MQ crontab 이 task 라우트를 여기로 보낸다 — prod-back 배포와 별도",
                          props={"repo": "zoomzoom-api", "process": "pm2 zoomzoom-api", "port": 4000, "host": "mq"},
                          source_ref="zoomzoom-services/docs/10-services/zoomzoom-api.md"))
        task_module = "module:zoomzoom-api/src/task"
        if task_module in col.nodes:
            col.edge(edge_rec(model.service_uid("zoomzoom-api", "mq"), "CONTAINS", task_module, SOURCE, source_ref="zoomzoom-services/docs/30-operations/scheduled-jobs.md"))


def _report(col: Collector, s: _Stats) -> None:
    lines = col.sections.setdefault("ts", [])
    for repo, rep in s.repos.items():
        counts = {k: v for k, v in rep.items() if isinstance(v, int)}
        lines += [f"### {repo}", "", f"- {counts}"]
        for k, v in rep.items():
            if isinstance(v, list) and v:
                lines += [f"- {k} ({len(v)}): " + ", ".join(f"`{x}`" for x in v[:12]) + (" …" if len(v) > 12 else "")]
        lines.append("")
    lines += ["### 저장소 간", "",
              f"- 스키마에 없는 테이블로 향한 READS/WRITES/MAPS_TO 버림: {s.dropped_rw}건" + (" — " + ", ".join(f"`{k}`×{v}" for k, v in s.unknown_table.most_common(10)) if s.unknown_table else ""),
              f"- consumer/front → back AccessRule 해석: {dict(s.http_resolved)} · 미해석(placeholder): {len(s.http_unresolved)}",
              f"- AccessRule → zoomzoom-api 라우트: {dict(s.rule_to_api)} · 짝 없는 규칙: {len(s.rule_unmatched)}", ""]
    if s.http_unresolved:
        lines += ["미해석 HTTP 호출 (최대 30):", ""] + [f"- `{x}`" for x in s.http_unresolved[:30]] + [""]
    if s.rule_unmatched:
        lines += ["api 라우트와 짝이 없는 AccessRule (최대 30):", ""] + [f"- `{x}`" for x in s.rule_unmatched[:30]] + [""]
