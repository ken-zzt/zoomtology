"""추출 결과를 병합·검증하고 번들(manifest + nodes.jsonl + edges.jsonl + report.md)을 쓴다. 1단계(ZDV-345)."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

from . import classification, curated, docs, laravel, php, schema_ddl, sources, ts
from .collect import Collector, Record
from .schema import Schema

EXTRACTORS = {"schema": "1", "classification": "1", "docs": "1", "php": "1", "ts": "1", "laravel": "1", "curated": "1"}


class BuildError(RuntimeError):
    pass


def run(out_dir: Path | None = None, update_state: bool = True, strict: bool = False) -> dict:
    today = dt.date.today().isoformat()
    now = dt.datetime.now(dt.UTC)
    schema = Schema.load()
    col = Collector()
    meta: dict[str, dict[str, str]] = {}

    # 1. 추출
    meta["schema"] = schema_ddl.extract(col, sources.latest_local_dump(), sources.latest_hub_dump())
    meta["classification"] = classification.extract(col, sources.AGENT_PRISM / "classification" / "tables.yaml")
    meta["docs"] = docs.extract(col)
    meta["php"] = php.extract(col, schema=schema)
    meta["ts"] = ts.extract(col, schema=schema)
    meta["laravel"] = laravel.extract(col, schema=schema)
    meta["placeholders"] = {"calls": str(php.ensure_placeholders(col))}
    meta["curated"] = curated.extract(col)

    # 2. 노드가 없는 관계는 버리고 report 에 적는다 (문서 부패·아직 안 만든 추출기)
    dangling: dict[str, list[str]] = defaultdict(list)
    kept_edges: list[Record] = []
    for (f, t, to), rec in col.edges.items():
        missing = [u for u in (f, to) if u not in col.nodes]
        if missing:
            for u in missing:
                dangling[u].append(f"{f} -{t}-> {to}")
            continue
        kept_edges.append(rec)

    # 3. 예약 접두사 (추출기 버그 방지)
    reserved = [u for u in col.nodes if any(u.startswith(p) for p in schema.reserved)]
    if reserved:
        raise BuildError(f"reserved prefix uids produced: {reserved[:5]}")

    # 4. first-seen / 드리프트
    first_seen = _read_first_seen()
    prev_uids = _read_uids()
    for uid, rec in col.nodes.items():
        rec["firstSeenAt"] = first_seen.get(uid, today)
        rec["lastSeenAt"] = today
        if rec.get("confidence") == "verified" and not rec.get("lastVerifiedAt"):
            rec["lastVerifiedAt"] = today
    for rec in kept_edges:
        rec["firstSeenAt"] = first_seen.get(_ekey(rec), today)
        rec["lastSeenAt"] = today
        if rec.get("confidence") == "verified" and not rec.get("lastVerifiedAt"):
            rec["lastVerifiedAt"] = today
    vanished = sorted(u for u in prev_uids if u not in col.nodes)
    # 드리프트: 지난 빌드에서 verified 였던 노드가 사라지면 tombstone(missing-from-source)으로 남긴다. auto 는 report 만.
    prev_verified = _read_verified()
    tombstones: list[str] = []
    for uid in vanished:
        if uid in prev_verified and uid not in col.nodes:
            v = prev_verified[uid]
            col.nodes[uid] = {
                "uid": uid, "label": v["label"], "name": v["name"], "summary": v.get("summary") or None,
                "props": {**_tombstone_props(v["label"]), "tombstone": True, "tombstonedAt": today, "note": "지난 빌드까지 verified 였으나 이번 소스에 없음 — 큐레이션 검토 필요"},
                "source": "manual", "confidence": "verified", "status": "missing-from-source", "sourceRef": "state/verified.tsv",
                "firstSeenAt": first_seen.get(uid, today), "lastSeenAt": today, "lastVerifiedAt": v.get("lastVerifiedAt") or today,
            }
            tombstones.append(uid)
    vanished_auto = [u for u in vanished if u not in prev_verified]

    # 5. 검증
    nodes = [col.nodes[u] for u in sorted(col.nodes)]
    edges = sorted(kept_edges, key=lambda e: (e["from"], e["type"], e["to"]))
    problems = schema.check_bundle(nodes, edges)
    if problems:
        head = "\n".join(str(p) for p in problems[:30])
        raise BuildError(f"{len(problems)} schema problem(s):\n{head}")

    # 6. manifest / report
    sha = sources.git_sha(sources.ZOOMTOLOGY) or "0" * 40
    dirty = sources.git_dirty(sources.ZOOMTOLOGY)
    version = f"{now:%Y%m%dT%H%MZ}-{sha[:7]}{'-dirty' if dirty else ''}"
    counts = {"nodes": dict(sorted(Counter(n["label"] for n in nodes).items())),
              "edges": dict(sorted(Counter(e["type"] for e in edges).items()))}
    src_state = source_state()
    src_warnings = source_warnings(src_state)
    content_sha = _content_sha(nodes, edges)
    previous = _read_previous_manifest()
    manifest = {
        "schemaVersion": schema.version, "version": version, "gitSha": sha, "dirty": dirty, "builtAt": now.isoformat(timespec="seconds"),
        "contentSha256": content_sha, "unchanged": bool(previous and previous.get("contentSha256") == content_sha),
        "previousVersion": previous.get("version") if previous else None,
        "extractors": EXTRACTORS, "inputs": meta, "sources": src_state, "sourceWarnings": src_warnings, "counts": counts,
        "drift": {"vanished": len(vanished), "tombstones": len(tombstones), "newNodes": sum(1 for u in col.nodes if first_seen.get(u, today) == today)},
        "smoke": [
            {"tool": "kg_node", "args": {"uid": "table:zoom_order"}},
            {"tool": "kg_node", "args": {"uid": "col:zoom_ms_requestpayment.status_id"}},
            {"tool": "kg_search", "args": {"q": "zoom_order", "limit": 5}},
        ],
    }
    report = _report(manifest, col, dangling, vanished_auto, tombstones, first_seen, today, previous)

    # 7. 쓰기
    out = out_dir or sources.DIST
    out.mkdir(parents=True, exist_ok=True)
    sources.LATEST.mkdir(parents=True, exist_ok=True)
    nodes_jsonl = "".join(json.dumps(n, ensure_ascii=False, sort_keys=True) + "\n" for n in nodes)
    edges_jsonl = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in edges)
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    bundle = out / f"zoomtology-{version}.tar.gz"
    with tarfile.open(bundle, "w:gz") as tar:
        for name, data in (("manifest.json", manifest_json), ("nodes.jsonl", nodes_jsonl), ("edges.jsonl", edges_jsonl), ("report.md", report)):
            b = data.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(b)
            info.mtime = int(now.timestamp())
            tar.addfile(info, io.BytesIO(b))
    (sources.LATEST / "manifest.json").write_text(manifest_json, encoding="utf-8")
    (sources.LATEST / "report.md").write_text(report, encoding="utf-8")
    (out / "nodes.jsonl").write_text(nodes_jsonl, encoding="utf-8")
    (out / "edges.jsonl").write_text(edges_jsonl, encoding="utf-8")

    if update_state:
        _write_first_seen(first_seen, nodes, edges, today)
        _write_uids(sorted(col.nodes))
        _write_verified(nodes)
    return {"bundle": str(bundle), "version": version, "contentSha256": content_sha, "unchanged": manifest["unchanged"],
            "counts": counts, "dangling": sum(len(v) for v in dangling.values()),
            "warnings": len(col.warnings), "vanished": len(vanished), "tombstones": len(tombstones),
            "sourceWarnings": src_warnings}


def source_repos() -> dict[str, Path]:
    """그래프 입력이 되는 저장소. 빌드는 작업 체크아웃을 그대로 읽으므로, 여기의 브랜치·변경이 곧 그래프 내용이다."""
    repos = {"zoomzoom-services": sources.HUB, "AgentPrism": sources.AGENT_PRISM}
    repos.update({r.name: r.root for r in php.default_repos()})
    repos.update({r.name: r.root for r in ts.default_repos()})
    repos[laravel.REPO] = sources.SERVICE / laravel.REPO
    return repos


def source_state(repos: dict[str, Path] | None = None) -> dict[str, dict]:
    defaults = sources.default_branches()
    state: dict[str, dict] = {}
    for name, path in sorted((repos or source_repos()).items()):
        sha = sources.git_sha(path)
        if sha:
            state[name] = {"sha": sha, "branch": sources.git_branch(path), "defaultBranch": defaults.get(name, "main"), "dirty": sources.git_dirty(path)}
    return state


def source_warnings(state: dict[str, dict]) -> list[str]:
    """메인 브랜치가 아니거나 커밋하지 않은 변경이 있는 저장소. 빌드를 막지는 않는다 — 그래프에 영향이 없는 브랜치도 있다."""
    result: list[str] = []
    for name, s in sorted(state.items()):
        if s["branch"] != s["defaultBranch"]:
            result.append(f"{name}: {s['branch'] or '분리된 HEAD'} 에 있습니다 (메인 {s['defaultBranch']})")
        if s["dirty"]:
            result.append(f"{name}: 커밋하지 않은 변경이 있습니다")
    return result


def _ekey(e: Record) -> str:
    return f"{e['from']} -{e['type']}-> {e['to']}"


def _read_first_seen() -> dict[str, str]:
    path = sources.STATE / "first-seen.tsv"
    result: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            if "\t" in line:
                uid, date = line.split("\t", 1)
                result[uid] = date
    return result


def _write_first_seen(existing: dict[str, str], nodes: list[Record], edges: list[Record], today: str) -> None:
    path = sources.STATE / "first-seen.tsv"
    new = [n["uid"] for n in nodes if n["uid"] not in existing] + [_ekey(e) for e in edges if _ekey(e) not in existing]
    if not path.exists():
        path.write_text("uid\tfirst_seen\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        for uid in new:
            fh.write(f"{uid}\t{today}\n")


def _content_sha(nodes: list[Record], edges: list[Record]) -> str:
    """입력이 같으면 같은 값. 날짜 거버넌스(firstSeenAt·lastSeenAt)는 뺀다 — 재현성 검사 기준."""
    h = hashlib.sha256()
    for rec in nodes:
        h.update(json.dumps({k: v for k, v in rec.items() if k not in ("firstSeenAt", "lastSeenAt")}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    h.update(b"--edges--\n")
    for rec in edges:
        h.update(json.dumps({k: v for k, v in rec.items() if k not in ("firstSeenAt", "lastSeenAt")}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _read_previous_manifest() -> dict | None:
    path = sources.LATEST / "manifest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _tombstone_props(label: str) -> dict:
    """라벨별 필수 props 의 빈 값(schema.yaml required) — tombstone 이 검증을 통과하게."""
    req = Schema.load().labels.get(label, {}).get("required", [])
    return {k: (0 if k in ("lineStart", "lineEnd") else "?") for k in req}


def _read_verified() -> dict[str, dict]:
    path = sources.STATE / "verified.tsv"
    out: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 4:
                out[parts[0]] = {"label": parts[1], "name": parts[2], "lastVerifiedAt": parts[3] or None, "summary": parts[4] if len(parts) > 4 else None}
    return out


def _write_verified(nodes: list[Record]) -> None:
    path = sources.STATE / "verified.tsv"
    lines = ["uid\tlabel\tname\tlastVerifiedAt\tsummary"]
    for n in nodes:
        if n.get("confidence") == "verified" and not n["props"].get("tombstone"):
            summary = (n.get("summary") or "").replace("\t", " ").replace("\n", " ")[:200]
            lines.append(f"{n['uid']}\t{n['label']}\t{n['name']}\t{n.get('lastVerifiedAt') or ''}\t{summary}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_uids() -> list[str]:
    path = sources.STATE / "uids.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _write_uids(uids: list[str]) -> None:
    (sources.STATE / "uids.txt").write_text("\n".join(uids) + ("\n" if uids else ""), encoding="utf-8")


def _report(manifest: dict, col: Collector, dangling: dict[str, list[str]], vanished: list[str], tombstones: list[str],
            first_seen: dict[str, str], today: str, previous: dict | None) -> str:
    lines = [f"# 빌드 report — {manifest['version']}", "",
             f"- builtAt: {manifest['builtAt']}  gitSha: {manifest['gitSha'][:7]}{' (dirty)' if manifest['dirty'] else ''}",
             f"- contentSha256: `{manifest['contentSha256'][:16]}…` — 이전 빌드({manifest.get('previousVersion') or '없음'})와 {'**같음** (입력 불변)' if manifest['unchanged'] else '다름'}",
             f"- inputs: {json.dumps(manifest['inputs'], ensure_ascii=False)}", ""]
    if manifest.get("sourceWarnings"):
        lines += ["## 소스 저장소 경고", "", "이 그래프에는 메인 브랜치에 없는 코드가 섞였을 수 있다.", ""] + [f"- {w}" for w in manifest["sourceWarnings"]] + [""]
    if previous and previous.get("counts"):
        lines += ["## 이전 빌드 대비", "", "| 종류 | 이전 | 지금 | 증감 |", "|---|---|---|---|"]
        for kind in ("nodes", "edges"):
            prev_c, cur_c = previous["counts"].get(kind, {}), manifest["counts"].get(kind, {})
            for k in sorted(set(prev_c) | set(cur_c)):
                a, b = prev_c.get(k, 0), cur_c.get(k, 0)
                if a != b:
                    lines.append(f"| {k} | {a} | {b} | {b - a:+d} |")
        if lines[-1].startswith("|---"):
            lines.append("| (변화 없음) | | | |")
        pd = previous.get("drift") or {}
        lines += ["", f"- 드리프트: 사라진 uid {manifest['drift']['vanished']} (이전 {pd.get('vanished', '?')}) · tombstone {manifest['drift']['tombstones']} · 새 노드 {manifest['drift']['newNodes']}", ""]
    lines += ["## 건수", "", "| 라벨 | 노드 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in manifest["counts"]["nodes"].items()]
    lines += ["", "| 관계 | 건수 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in manifest["counts"]["edges"].items()]
    new_nodes = sum(1 for u in col.nodes if first_seen.get(u, today) == today)
    lines += ["", f"- 이번 빌드에 처음 보인 노드: {new_nodes}", f"- 지난 빌드엔 있었는데 사라진 uid(auto, 삭제): {len(vanished)}", f"- tombstone(verified 였는데 소스에 없음, missing-from-source 로 유지): {len(tombstones)}"]
    if tombstones:
        lines += ["", "### tombstone — 큐레이션 검토 필요 (curated 에서 지우거나 소스를 확인)", ""] + [f"- `{u}`" for u in tombstones[:100]]
    if vanished:
        lines += ["", "### 사라진 uid (auto — 삭제됨)", ""] + [f"- `{u}`" for u in vanished[:100]]
    status_counts = Counter(n.get("status") for n in col.nodes.values())
    lines += ["", f"- status: {dict(status_counts)}"]
    for name, body in col.sections.items():
        lines += ["", f"## 추출기 report — {name}", ""] + body
    lines += ["", "## 추출기 경고", ""]
    lines += [f"- [{w.extractor}] {w.message}" for w in col.warnings] or ["- 없음"]
    lines += ["", f"## 노드가 없어 버린 관계 ({sum(len(v) for v in dangling.values())}건, 대상 uid {len(dangling)}개)", "",
              "문서가 가리키는 컬럼이 스키마에 없거나(문서 부패), 아직 추출기가 없는 코드 유닛(2·3단계)이다.", ""]
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for uid in dangling:
        by_prefix[uid.split(":", 1)[0]].append(uid)
    for prefix, uids in sorted(by_prefix.items()):
        lines.append(f"- `{prefix}:` {len(uids)}개" + (f" — 예: " + ", ".join(f"`{u}`" for u in sorted(uids)[:8]) if uids else ""))
    lines += ["", f"## 노드가 없어 버린 부분 레코드 ({len(col.dropped_partials)}건)", ""]
    dp = Counter(f"{uid.split(':',1)[0]}: ← {src}" for uid, src in col.dropped_partials)
    lines += [f"- {k}: {v}" for k, v in sorted(dp.items())] or ["- 없음"]
    col_dropped = sorted({uid for uid, src in col.dropped_partials if uid.startswith("col:")})
    if col_dropped:
        lines += ["", "문서에는 있는데 스키마엔 없는 컬럼(검토 필요):", ""] + [f"- `{u}`" for u in col_dropped[:60]]
    return "\n".join(lines) + "\n"
