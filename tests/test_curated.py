"""curated 오버레이 — 작은 그래프 위에 fixture YAML 을 얹어 도메인·논리 FK·폐기·enum·규칙·프로세스와 충돌 report 를 고정한다."""

import json
from pathlib import Path

from zoomtology import curated, model
from zoomtology.collect import Collector, edge_rec, node_rec
from zoomtology.schema import Schema

FIX = Path(__file__).parent / "fixtures" / "curated"


def _graph() -> Collector:
    col = Collector()
    for t in ("zoom_order", "zoom_product", "zoom_seller_charge"):
        col.node(node_rec(model.table_uid(t), "Table", t, "schema@1", props={"db": "zzt"}))
    for t, c, pk in (("zoom_order", "product_id", False), ("zoom_product", "product_id", True), ("zoom_order", "order_status_id", False),
                     ("zoom_seller_charge", "seller_id", False)):
        col.node(node_rec(model.col_uid(t, c), "Column", c, "schema@1", props={"type": "int", "nullable": False, "isPk": pk}))
    col.node(node_rec("enum:zoom_order.order_status_id=1", "EnumValue", "1", "doc:x.md", props={"value": "1", "origin": "status-codes", "meaning": "요청"}))
    col.edge(edge_rec("col:zoom_order.order_status_id", "HAS_VALUE", "enum:zoom_order.order_status_id=1", "doc:x.md"))
    col.node(node_rec("rule:auto-reject", "BusinessRule", "auto-reject", "doc:p.md", props={"title": "자동거절", "doc": "p.md"}))
    f = "system/library/zoomtu/transactions.php"
    for m in ("addTransaction", "addTransactionV2"):
        col.node(node_rec(model.code_uid("zoomzoom-admin", f, "ZZTTransactions", m), "CodeUnit", m, "php@1", props={"kind": "method", "lineStart": 1, "lineEnd": 2}))
    caller = model.code_uid("zoomzoom-admin", "admin/controller/x.php", "ControllerX", "run")
    col.node(node_rec(caller, "CodeUnit", "run", "php@1", props={"kind": "method", "lineStart": 1, "lineEnd": 2}))
    col.edge(edge_rec(caller, "CALLS", model.code_uid("zoomzoom-admin", f, "ZZTTransactions", "addTransactionV2"), "php@1", props={"kind": "zoomtu", "lines": [1]}))
    for p, area in (("catalog/controller/product/product.php", "catalog"), ("catalog/controller/task/task.php", "catalog"), ("admin/controller/cron/tasks.php", "admin")):
        col.node(node_rec(model.file_uid("zoomzoom-admin", p), "File", p, "php@1", props={"repo": "zoomzoom-admin", "path": p, "lang": "php"}))
    for r, area in (("product/product", "catalog"), ("task/task/rejectorderafterweek", "catalog"), ("cron/tasks/statuscheck", "admin")):
        col.node(node_rec(model.opencart_route_uid("zoomzoom-admin", r), "Route", r, "php@1", props={"repo": "zoomzoom-admin", "kind": "opencart", "path": r, "area": area}))
    col.node(node_rec("queue:order", "Queue", "order", "ts@1", props={"role": "order"}))
    col.node(node_rec("cron:admin/cron/tasks/statuscheck", "CronJob", "statuscheck", "doc:s.md", props={"schedule": "3 * * * *", "host": "admin"}))
    return col


def _run():
    col = _graph()
    meta = curated.extract(col, FIX)
    return col, meta


def test_domains_references_enums_rules_process():
    col, meta = _run()
    assert col.nodes["domain:order"]["props"]["nameKo"] == "주문" and col.nodes["domain:order"]["source"] == "manual"
    members = {f for (f, t, to) in col.edges if t == "BELONGS_TO_DOMAIN" and to == "domain:order"}
    assert members == {"table:zoom_order", "table:zoom_product", "route:zoomzoom-admin route=cron/tasks/statuscheck", "cron:admin/cron/tasks/statuscheck"}   # glob 확장 포함
    ref = col.edges[("col:zoom_order.product_id", "REFERENCES", "col:zoom_product.product_id")]
    assert ref["source"] == "manual" and ref["confidence"] == "verified" and ref["lastVerifiedAt"] == "2026-10-28" and ref["props"]["kind"] == "logical"
    e1 = col.nodes["enum:zoom_order.order_status_id=1"]
    assert e1["props"]["meaning"] == "예약요청" and e1["props"]["origin"] == "status-codes" and e1["props"]["alt"]["doc:x.md"]["props"]["meaning"] == "요청"
    assert "enum:zoom_order.order_status_id=6" in col.nodes and ("col:zoom_order.order_status_id", "HAS_VALUE", "enum:zoom_order.order_status_id=6") in col.edges
    impl = col.edges[("cron:admin/cron/tasks/statuscheck", "IMPLEMENTS_RULE", "rule:auto-reject")]
    assert impl["props"] == {"level": "unit", "role": "크론"} and col.nodes["rule:auto-reject"]["props"]["curated"] is True
    doc = col.nodes["doc:zoomtology/curated/processes/pilot.yaml"]
    assert doc["props"]["type"] == "process" and [s["id"] for s in doc["props"]["steps"]] == ["order", "settle"]
    assert col.edges[("table:zoom_order", "DOCUMENTED_BY", doc["uid"])]["props"]["section"] == "order"
    assert col.nodes["queue:order"]["props"]["phpConstants"] == ["SEND_ORDER_QUEUE"]
    assert meta["references"] == "1" and meta["domains"] == "1"


def test_retired_and_supersedes():
    col, _ = _run()
    old = "code:zoomzoom-admin/system/library/zoomtu/transactions.php#ZZTTransactions::addTransactionV2"
    new = "code:zoomzoom-admin/system/library/zoomtu/transactions.php#ZZTTransactions::addTransaction"
    assert col.nodes[old]["status"] == "retired" and col.nodes[old]["props"]["retiredBy"] == "add-transaction-v2"
    assert col.nodes[new]["status"] == "active"
    assert (new, "SUPERSEDES", old) in col.edges and col.edges[(new, "SUPERSEDES", old)]["status"] == "active"
    caller = "code:zoomzoom-admin/admin/controller/x.php#ControllerX::run"
    assert col.edges[(caller, "CALLS", old)]["status"] == "retired" and col.nodes[caller]["status"] == "active"
    assert col.nodes["file:zoomzoom-admin/catalog/controller/product/product.php"]["status"] == "retired"
    assert col.nodes["route:zoomzoom-admin route=product/product"]["status"] == "retired"
    assert col.nodes["file:zoomzoom-admin/catalog/controller/task/task.php"]["status"] == "active"         # except
    assert col.nodes["route:zoomzoom-admin route=task/task/rejectorderafterweek"]["status"] == "active"
    assert col.nodes["file:zoomzoom-admin/admin/controller/cron/tasks.php"]["status"] == "active"


def test_conflicts_and_missing_are_reported_not_fatal():
    col, _ = _run()
    report = "\n".join(col.sections["curated"])
    assert "col:zoom_nope.x" in report                      # 없는 uid 참조
    assert "DDL FK 는 반대 방향" in report or "seller_id" in report
    assert "verified 인데 lastVerifiedAt 이 없음" in report  # 날짜 없는 verified 항목은 적용 안 함
    assert "domain:ghost" not in col.nodes
    assert "의미 불일치" in report


def test_output_passes_schema():
    col, _ = _run()
    schema = Schema.load()
    nodes = list(col.nodes.values())
    edges = [rec for (f, _, t), rec in col.edges.items() if f in col.nodes and t in col.nodes]
    for rec in nodes + edges:
        rec["firstSeenAt"] = rec["lastSeenAt"] = "2026-10-28"
    assert schema.check_bundle(nodes, edges) == []
    assert "SELECT" not in json.dumps(nodes + edges, ensure_ascii=False)
