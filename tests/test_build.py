"""build 의 드리프트·재현성 보조 — contentSha 는 날짜 거버넌스에 무관, verified 노드가 사라지면 tombstone, 이전 빌드 대비 델타."""

import json
import subprocess
from pathlib import Path

from zoomtology import build, sources
from zoomtology.collect import node_rec


def _rec(uid, label="Table", **kw):
    r = node_rec(uid, label, uid.split(":", 1)[1], "schema@1", props={"db": "zzt"})
    r.update(kw)
    return r


def test_content_sha_ignores_seen_dates_but_not_content():
    a = [_rec("table:zoom_order", firstSeenAt="2026-10-01", lastSeenAt="2026-10-01")]
    b = [_rec("table:zoom_order", firstSeenAt="2026-10-28", lastSeenAt="2026-10-28")]
    assert build._content_sha(a, []) == build._content_sha(b, [])
    c = [_rec("table:zoom_order", summary="바뀜")]
    assert build._content_sha(c, []) != build._content_sha(a, [])


def test_verified_state_roundtrip_and_tombstone_props(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "STATE", tmp_path)
    nodes = [_rec("table:zoom_order", confidence="verified", lastVerifiedAt="2026-10-28", summary="주문\t표"),
             _rec("table:zoom_x", confidence="auto")]
    build._write_verified(nodes)
    v = build._read_verified()
    assert list(v) == ["table:zoom_order"] and v["table:zoom_order"]["lastVerifiedAt"] == "2026-10-28" and "\t" not in v["table:zoom_order"]["summary"]
    assert build._tombstone_props("CodeUnit") == {"kind": "?", "lineStart": 0, "lineEnd": 0}
    assert build._tombstone_props("Table") == {"db": "?"}


def test_report_delta_and_tombstone_section(tmp_path):
    manifest = {"version": "v2", "builtAt": "t", "gitSha": "abcdef0", "dirty": False, "contentSha256": "f" * 64, "unchanged": False,
                "previousVersion": "v1", "inputs": {}, "counts": {"nodes": {"Table": 3, "Domain": 1}, "edges": {"READS": 5}},
                "drift": {"vanished": 1, "tombstones": 1, "newNodes": 0}}
    previous = {"version": "v1", "counts": {"nodes": {"Table": 2}, "edges": {"READS": 5}}, "drift": {"vanished": 0}}
    from zoomtology.collect import Collector
    col = Collector()
    text = build._report(manifest, col, {}, ["code:x/y.php#A::b"], ["table:gone"], {}, "2026-10-28", previous)
    assert "| Table | 2 | 3 | +1 |" in text and "| Domain | 0 | 1 | +1 |" in text and "READS" not in text.split("## 이전 빌드 대비")[1].split("##")[0]
    assert "tombstone" in text and "`table:gone`" in text and "`code:x/y.php#A::b`" in text


def _state(branch="main", default="main", dirty=False):
    return {"sha": "a" * 40, "branch": branch, "defaultBranch": default, "dirty": dirty}


def test_source_warnings_flag_only_off_main_or_dirty_repos():
    state = {"zoomzoom-admin": _state("master", "master"), "zoomzoom-api": _state("ZDV-385"), "zoomzoom-back": _state(dirty=True), "data-api": _state(None)}
    warnings = build.source_warnings(state)
    assert len(warnings) == 3
    assert any(w.startswith("zoomzoom-api: ZDV-385") for w in warnings)
    assert any(w.startswith("zoomzoom-back:") and "변경" in w for w in warnings)
    assert any(w.startswith("data-api:") and "HEAD" in w for w in warnings)
    assert not any(w.startswith("zoomzoom-admin") for w in warnings)


def test_source_state_reads_branch_and_default_from_repos_tsv(tmp_path, monkeypatch):
    hub = tmp_path / "hub"
    (hub / "tools").mkdir(parents=True)
    (hub / "tools" / "repos.tsv").write_text("# note\n#name\tdir\tremote\tbranch\nlegacy\t../legacy\tx\tmaster\n", encoding="utf-8")
    monkeypatch.setattr(sources, "HUB", hub)
    repo = tmp_path / "legacy"
    repo.mkdir()
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(git + ["init", "-q", "-b", "ZDV-1"], check=True)
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "x"], check=True)
    state = build.source_state({"legacy": repo, "unlisted": repo, "absent": tmp_path / "nope"})
    assert state["legacy"]["branch"] == "ZDV-1" and state["legacy"]["defaultBranch"] == "master" and state["legacy"]["dirty"] is False
    assert state["unlisted"]["defaultBranch"] == "main" and "absent" not in state


def test_source_repos_cover_every_extracted_repo():
    repos = build.source_repos()
    assert {"zoomzoom-admin", "zoomzoom-partners", "zoomzoom-auth", "zoomzoom-api", "message-consumer", "zoomzoom-back",
            "external-api", "data-api", "zoomzoom-front", "zoomzoom-services", "AgentPrism"} == set(repos)


def test_report_shows_source_warnings_near_the_top():
    from zoomtology.collect import Collector
    manifest = {"version": "v", "builtAt": "t", "gitSha": "abcdef0", "dirty": False, "contentSha256": "f" * 64, "unchanged": False,
                "previousVersion": None, "inputs": {}, "counts": {"nodes": {}, "edges": {}}, "drift": {"vanished": 0, "tombstones": 0, "newNodes": 0},
                "sourceWarnings": ["zoomzoom-api: ZDV-385 에 있습니다 (메인 main)"]}
    text = build._report(manifest, Collector(), {}, [], [], {}, "2026-10-31", None)
    assert text.index("## 소스 저장소 경고") < text.index("## 건수") and "ZDV-385" in text
    manifest["sourceWarnings"] = []
    assert "소스 저장소 경고" not in build._report(manifest, Collector(), {}, [], [], {}, "2026-10-31", None)
