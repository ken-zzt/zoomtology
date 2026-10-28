"""ontology/schema.yaml 검증기 테스트 — fixture 는 통과하고, 규칙 위반은 잡혀야 한다."""

import json
from pathlib import Path

import pytest

from zoomtology.guard import is_denied_path
from zoomtology.schema import Schema

FIX = Path(__file__).parent / "fixtures"


def _jsonl(name):
    return [json.loads(l) for l in (FIX / name).read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture(scope="module")
def schema():
    return Schema.load()


def _node(**over):
    base = {
        "uid": "table:zoom_order", "label": "Table", "name": "zoom_order",
        "props": {"db": "zzt"}, "source": "schema@1", "confidence": "auto", "status": "active",
        "firstSeenAt": "2026-10-28", "lastSeenAt": "2026-10-28",
    }
    base.update(over)
    return base


def test_schema_declares_17_labels_and_20_edges(schema):
    assert len(schema.labels) == 17
    assert len(schema.edges) == 20
    assert schema.reserved == ["dept:", "role:", "process:", "person:"]


def test_fixture_bundle_is_valid(schema):
    problems = schema.check_bundle(_jsonl("nodes.jsonl"), _jsonl("edges.jsonl"))
    assert problems == [], "\n".join(map(str, problems))


def test_unknown_label_rejected(schema):
    assert any("unknown label" in str(p) for p in schema.check_node(_node(label="Tabel")))


def test_uid_pattern_enforced(schema):
    assert any("pattern" in str(p) for p in schema.check_node(_node(uid="table:zoom order")))


def test_reserved_prefix_rejected(schema):
    rec = _node(uid="dept:cs", label="Domain", props={"nameKo": "CS"})
    assert any("reserved prefix" in str(p) for p in schema.check_node(rec))


def test_required_prop_enforced(schema):
    assert any("missing required prop 'db'" in str(p) for p in schema.check_node(_node(props={})))


def test_forbidden_code_body_rejected(schema):
    rec = _node(
        uid="code:zoomzoom-api/src/a.ts#X::y", label="CodeUnit", name="X::y",
        props={"kind": "method", "lineStart": 1, "lineEnd": 2, "body": "return 1"},
    )
    assert any("forbidden prop 'body'" in str(p) for p in schema.check_node(rec))


def test_verified_requires_last_verified_at(schema):
    rec = _node(source="manual", confidence="verified")
    assert any("requires lastVerifiedAt" in str(p) for p in schema.check_node(rec))


def test_sql_text_in_props_rejected(schema):
    rec = _node(props={"db": "zzt", "note": "SELECT * FROM zoom_order WHERE id = 1"})
    assert any("denied pattern" in str(p) for p in schema.check_node(rec))


def test_secret_in_props_rejected(schema):
    rec = _node(props={"db": "zzt", "note": "password = hunter2hunter2"})
    assert any("denied pattern" in str(p) for p in schema.check_node(rec))


def test_edge_label_constraint(schema):
    labels = {"table:zoom_order": "Table", "domain:settlement": "Domain"}
    bad = {"from": "domain:settlement", "type": "READS", "to": "table:zoom_order", "props": {},
           "source": "manual", "confidence": "verified", "status": "active",
           "firstSeenAt": "2026-10-28", "lastSeenAt": "2026-10-28", "lastVerifiedAt": "2026-10-28"}
    assert any("not allowed for READS" in str(p) for p in schema.check_edge(bad, labels))


def test_dangling_edge_detected(schema):
    nodes = _jsonl("nodes.jsonl")
    edges = _jsonl("edges.jsonl") + [dict(_jsonl("edges.jsonl")[0], to="file:zoomzoom-admin/nope.php")]
    assert any("not found in nodes" in str(p) for p in schema.check_bundle(nodes, edges))


@pytest.mark.parametrize("path,denied", [
    ("zoomzoom-admin/scripts/stats_cron.sh", True),
    ("zoomzoom-admin/config.php", True),
    ("zoomzoom-api/.env.production", True),
    ("zoomzoom-api/node_modules/x/index.js", True),
    ("zoomzoom-services/reference/server-config/zzt-cwagent.la-back.json", True),
    ("zoomzoom-admin/system/library/zoomtu/order_info.php", False),
    ("zoomzoom-api/src/order/order.entity.ts", False),
])
def test_denied_paths(schema, path, denied):
    assert is_denied_path(path, schema) is denied
