"""curated/ 오버레이 — 사람이 쓴 YAML 을 그래프에 얹는다 (4단계, ZDV-348). 우선순위 manual > doc > extractor (ADR 0005).

파일(전부 선택):
- domains.yaml        Domain 노드 + BELONGS_TO_DOMAIN (members 는 uid 또는 {glob})
- references.yaml     논리 FK REFERENCES{kind: logical, evidence}
- retired.yaml        폐기 플래그(match: uid_glob | label+props, except) + SUPERSEDES
- enum-overrides.yaml EnumValue 의미 보정 (values) · 코드 static 배열→컬럼 매핑 (arrays, php.py 가 읽는다)
- queues.yaml         PHP SEND_*_QUEUE 상수 ↔ 큐 역할 (php.py 가 읽는다)
- rules/*.yaml        BusinessRule ← IMPLEMENTS_RULE (유닛 수준)
- processes/*.yaml    프로세스 → v1 은 Doc 노드 + DOCUMENTED_BY

파일마다 `confidence: auto|verified`, `lastVerifiedAt`, `verifiedBy` 를 머리에 둔다(항목에서 덮어쓸 수 있다).
verified 인데 lastVerifiedAt 이 없으면 그 파일은 적용하지 않고 report 에 적는다. 충돌은 전부 report 에 남긴다.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

from . import model
from .collect import Collector, edge_rec, node_rec
from .sources import ZOOMTOLOGY

SOURCE = "manual"
CURATED = ZOOMTOLOGY / "curated"


@dataclass
class _Stats:
    files: list[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    missing: list[str] = field(default_factory=list)          # 참조한 uid 가 그래프에 없음
    conflicts: list[str] = field(default_factory=list)        # FK 모순·enum 불일치·supersede 대상 없음 등
    skipped: list[str] = field(default_factory=list)          # verified 인데 날짜 없음 등
    retired_rules: Counter = field(default_factory=Counter)


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _gov(doc: dict, item: dict | None = None) -> tuple[str, str | None, str | None]:
    """(confidence, lastVerifiedAt, verifiedBy) — 항목 값이 파일 값을 덮는다."""
    item = item or {}
    conf = item.get("confidence", doc.get("confidence", "auto"))
    lv = item.get("lastVerifiedAt", doc.get("lastVerifiedAt"))
    vb = item.get("verifiedBy", doc.get("verifiedBy"))
    return conf, (str(lv) if lv else None), vb


def _check_gov(stats: _Stats, where: str, conf: str, lv: str | None) -> bool:
    if conf not in ("auto", "verified"):
        stats.skipped.append(f"{where}: confidence {conf!r} 는 auto|verified 가 아님")
        return False
    if conf == "verified" and not lv:
        stats.skipped.append(f"{where}: verified 인데 lastVerifiedAt 이 없음")
        return False
    return True


def _expand(col: Collector, member, stats: _Stats, where: str) -> list[str]:
    """uid 문자열 또는 {glob: pattern[, label: L]} 를 그래프에 있는 uid 목록으로."""
    if isinstance(member, str):
        if member in col.nodes:
            return [member]
        stats.missing.append(f"{where}: {member}")
        return []
    if isinstance(member, dict) and "glob" in member:
        label = member.get("label")
        hits = [u for u, n in col.nodes.items() if fnmatchcase(u, member["glob"]) and (label is None or n["label"] == label)]
        if not hits:
            stats.missing.append(f"{where}: glob {member['glob']!r} 에 맞는 노드 없음")
        return hits
    stats.skipped.append(f"{where}: 알 수 없는 member {member!r}")
    return []


# --- 1. domains ----------------------------------------------------------------------------

def apply_domains(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    for d in doc.get("domains", []):
        conf, lv, vb = _gov(doc, d)
        if not _check_gov(stats, f"{ref}#{d.get('uid')}", conf, lv):
            continue
        uid = d["uid"]
        props = {"nameKo": d["nameKo"], "aliases": d.get("aliases", []), "curated": True}
        if vb:
            props["verifiedBy"] = vb
        col.node(node_rec(uid, "Domain", d.get("name", uid.split(":", 1)[1]), SOURCE, summary=d.get("summary"), props=props,
                          confidence=conf, source_ref=ref, last_verified_at=lv))
        stats.counts["domains"] += 1
        for m in d.get("members", []):
            for target in _expand(col, m, stats, f"{ref}#{uid}"):
                col.edge(edge_rec(target, "BELONGS_TO_DOMAIN", uid, SOURCE, confidence=conf, source_ref=ref, last_verified_at=lv))
                stats.counts["belongs_to_domain"] += 1


# --- 2. references -------------------------------------------------------------------------

def apply_references(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    for r in doc.get("references", []):
        conf, lv, vb = _gov(doc, r)
        where = f"{ref}: {r.get('from')} → {r.get('to')}"
        if not _check_gov(stats, where, conf, lv):
            continue
        f, t = r["from"], r["to"]
        if f not in col.nodes or t not in col.nodes:
            stats.missing.append(where)
            continue
        if (t, "REFERENCES", f) in col.edges and col.edges[(t, "REFERENCES", f)]["props"].get("kind") == "fk":
            stats.conflicts.append(f"{where}: DDL FK 는 반대 방향")
            continue
        props = {"kind": "logical", "evidence": list(r.get("evidence", []))}
        if r.get("note"):
            props["note"] = r["note"]
        if vb:
            props["verifiedBy"] = vb
        col.edge(edge_rec(f, "REFERENCES", t, SOURCE, props=props, confidence=conf, source_ref=ref, last_verified_at=lv))
        stats.counts["references"] += 1


# --- 3. retired ----------------------------------------------------------------------------

def _matches(uid: str, node: dict, rule: dict) -> bool:
    if "uid_glob" in rule:
        return fnmatchcase(uid, rule["uid_glob"])
    if "label" in rule or "props" in rule:
        if "label" in rule and node["label"] != rule["label"]:
            return False
        for k, v in (rule.get("props") or {}).items():
            if node["props"].get(k) != v:
                return False
        return True
    return False


def apply_retired(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    retired_uids: set[str] = set()
    for item in doc.get("retired", []):
        conf, lv, vb = _gov(doc, item)
        name = item.get("name", "?")
        if not _check_gov(stats, f"{ref}#{name}", conf, lv):
            continue
        hits: set[str] = set(item.get("uids", []))
        for u in list(hits):
            if u not in col.nodes:
                stats.missing.append(f"{ref}#{name}: {u}")
                hits.discard(u)
        if item.get("match"):
            for uid, node in col.nodes.items():
                if any(_matches(uid, node, m) for m in item["match"]) and not any(_matches(uid, node, x) for x in item.get("except", [])):
                    hits.add(uid)
        for uid in hits:
            n = col.nodes[uid]
            n["status"] = "retired"
            n["props"]["retiredBy"] = name
            n["props"]["retiredReason"] = item.get("reason")
            if item.get("evidence"):
                n["props"]["retiredEvidence"] = item["evidence"]
            if conf == "verified":
                n["confidence"] = "verified"
                n["lastVerifiedAt"] = lv
                if vb:
                    n["props"]["verifiedBy"] = vb
        retired_uids |= hits
        stats.retired_rules[name] += len(hits)
        new = item.get("supersededBy")
        if new:
            if new not in col.nodes:
                stats.conflicts.append(f"{ref}#{name}: supersededBy {new} 가 그래프에 없음")
            else:
                for old in item.get("uids", []):
                    if old in col.nodes:
                        col.edge(edge_rec(new, "SUPERSEDES", old, SOURCE, props={"reason": item.get("reason")}, confidence=conf, source_ref=ref, last_verified_at=lv))
                        stats.counts["supersedes"] += 1
    # 폐기 노드에 닿는 관계도 retired (호출자 관계 포함). SUPERSEDES 는 그대로 둔다.
    n_edges = 0
    for (f, t, to), e in col.edges.items():
        if t != "SUPERSEDES" and (f in retired_uids or to in retired_uids) and e.get("status") != "retired":
            e["status"] = "retired"
            e["props"]["retiredVia"] = f if f in retired_uids else to
            n_edges += 1
    stats.counts["retired_nodes"] += len(retired_uids)
    stats.counts["retired_edges"] += n_edges


# --- 4. enum overrides ---------------------------------------------------------------------

def apply_enums(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    for item in doc.get("values", []):
        conf, lv, vb = _gov(doc, item)
        table, column = item["column"].split(".", 1)
        if not _check_gov(stats, f"{ref}#{item['column']}", conf, lv):
            continue
        cuid = model.col_uid(table, column)
        if cuid not in col.nodes:
            stats.missing.append(f"{ref}: {cuid}")
            continue
        for value, spec in (item.get("values") or {}).items():
            spec = spec if isinstance(spec, dict) else {"meaning": str(spec)}
            euid = model.enum_uid(table, column, value)
            existing = col.nodes.get(euid)
            if existing and existing["props"].get("meaning") and spec.get("meaning") and existing["props"]["meaning"] != spec["meaning"]:
                stats.conflicts.append(f"{euid}: 의미 불일치 — {existing['source']} {existing['props']['meaning']!r} → manual {spec['meaning']!r} (manual 적용, alt 에 보존)")
            props = {"value": str(value), "origin": "manual", "meaning": spec.get("meaning"), "label": spec.get("label")}
            props = {k: v for k, v in props.items() if v is not None}
            if spec.get("note"):
                props["note"] = spec["note"]
            rec = node_rec(euid, "EnumValue", str(value), SOURCE, summary=spec.get("meaning"), props=props, confidence=conf, source_ref=ref, last_verified_at=lv)
            if existing:
                rec["props"].pop("origin", None)         # 원래 출처(status-codes/ddl/code)는 유지하고 의미만 덮는다
                col.node(rec)
            else:
                col.node(rec)
                col.edge(edge_rec(cuid, "HAS_VALUE", euid, SOURCE, confidence=conf, source_ref=ref, last_verified_at=lv))
            stats.counts["enum_values"] += 1


# --- 5. queues -----------------------------------------------------------------------------

def apply_queues(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    conf, lv, vb = _gov(doc)
    for const, role in (doc.get("constants") or {}).items():
        quid = model.queue_uid(role)
        q = col.nodes.get(quid)
        if q is None:
            col.node(node_rec(quid, "Queue", role, SOURCE, props={"role": role, "note": "큐 발행·소비 코드가 그래프에 없어 상수 매핑으로만 안다"},
                              confidence=conf, source_ref=ref, last_verified_at=lv))
            q = col.nodes[quid]
        q["props"].setdefault("phpConstants", [])
        if const not in q["props"]["phpConstants"]:
            q["props"]["phpConstants"].append(const)
        q["props"]["phpConstants"].sort()
        stats.counts["queue_constants"] += 1


# --- 6. rules ------------------------------------------------------------------------------

def apply_rule(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    rule = doc.get("rule")
    if not rule:
        stats.skipped.append(f"{ref}: rule 이 없음")
        return
    if rule not in col.nodes:
        stats.missing.append(f"{ref}: {rule}")
        return
    col.nodes[rule]["props"]["curated"] = True
    for u in doc.get("units", []):
        conf, lv, vb = _gov(doc, u)
        uid = u["uid"]
        if not _check_gov(stats, f"{ref}#{uid}", conf, lv):
            continue
        if uid not in col.nodes:
            stats.missing.append(f"{ref}: {uid}")
            continue
        props = {"level": "unit"}
        if u.get("role"):
            props["role"] = u["role"]
        if u.get("section"):
            props["section"] = u["section"]
        col.edge(edge_rec(uid, "IMPLEMENTS_RULE", rule, SOURCE, props=props, confidence=conf, source_ref=ref, last_verified_at=lv))
        stats.counts["implements_rule"] += 1


# --- 7. processes (v1: Doc 노드) -----------------------------------------------------------

def apply_process(col: Collector, doc: dict, stats: _Stats, ref: str) -> None:
    conf, lv, vb = _gov(doc)
    uid = doc.get("uid") or f"doc:zoomtology/{ref}"
    if not _check_gov(stats, ref, conf, lv):
        return
    steps = doc.get("steps", [])
    col.node(node_rec(uid, "Doc", doc.get("title", ref), SOURCE, summary=doc.get("summary"),
                      props={"type": "process", "status": doc.get("status", "draft"), "title": doc.get("title"),
                             "steps": [{"id": s["id"], "name": s.get("name"), "actor": s.get("actor")} for s in steps], "curated": True},
                      confidence=conf, source_ref=ref, last_verified_at=lv))
    stats.counts["processes"] += 1
    for s in steps:
        for r in s.get("refs", []):
            for target in _expand(col, r, stats, f"{ref}#{s['id']}"):
                col.edge(edge_rec(target, "DOCUMENTED_BY", uid, SOURCE, props={"section": s["id"]}, confidence=conf, source_ref=ref, last_verified_at=lv))
                stats.counts["process_refs"] += 1


# --- 진입 ----------------------------------------------------------------------------------

def extract(col: Collector, root: Path | None = None) -> dict[str, str]:
    root = root or CURATED
    stats = _Stats()
    rel = lambda p: f"zoomtology/curated/{p.relative_to(root).as_posix()}"  # noqa: E731
    order = [("domains.yaml", apply_domains), ("references.yaml", apply_references), ("enum-overrides.yaml", apply_enums),
             ("queues.yaml", apply_queues)]
    for name, fn in order:
        p = root / name
        doc = _load(p)
        if doc is None:
            continue
        stats.files.append(name)
        fn(col, doc, stats, rel(p))
    for p in sorted((root / "rules").glob("*.yaml")):
        doc = _load(p)
        if doc:
            stats.files.append(f"rules/{p.name}")
            apply_rule(col, doc, stats, rel(p))
    for p in sorted((root / "processes").glob("*.yaml")):
        doc = _load(p)
        if doc:
            stats.files.append(f"processes/{p.name}")
            apply_process(col, doc, stats, rel(p))
    # retired 는 맨 끝 — 위에서 만든 관계까지 포함해 retired 를 전파한다
    p = root / "retired.yaml"
    doc = _load(p)
    if doc is not None:
        stats.files.append("retired.yaml")
        apply_retired(col, doc, stats, rel(p))
    _report(col, stats)
    return {"files": ",".join(stats.files) or "-", **{k: str(v) for k, v in sorted(stats.counts.items())}}


def _report(col: Collector, s: _Stats) -> None:
    lines = col.sections.setdefault("curated", [])
    lines += [f"- 파일: {', '.join(s.files) or '없음'}", f"- 건수: {dict(s.counts)}", f"- 폐기 규칙별 노드 수: {dict(s.retired_rules)}", ""]
    if s.missing:
        lines += [f"그래프에 없는 uid 를 참조 ({len(s.missing)}건, 최대 40):", ""] + [f"- `{x}`" for x in s.missing[:40]] + [""]
    if s.conflicts:
        lines += [f"충돌 ({len(s.conflicts)}건):", ""] + [f"- {x}" for x in s.conflicts[:40]] + [""]
    if s.skipped:
        lines += [f"적용하지 않음 ({len(s.skipped)}건):", ""] + [f"- {x}" for x in s.skipped[:40]] + [""]
