"""build 의 드리프트·재현성 보조 — contentSha 는 날짜 거버넌스에 무관, verified 노드가 사라지면 tombstone, 이전 빌드 대비 델타."""

import json
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
