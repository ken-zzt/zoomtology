"""php 추출기 — 작은 fixture 저장소(tests/fixtures/php/zoomzoom-admin)로 핵심 동작을 고정한다."""

import json
from pathlib import Path

from zoomtology import model, php, phplex, sqlshape
from zoomtology.collect import Collector, node_rec
from zoomtology.schema import Schema

FIX = Path(__file__).parent / "fixtures" / "php"
REPO = "zoomzoom-admin"


def _seed(col: Collector) -> None:
    col.node(node_rec("repo:zoomzoom-admin", "Repo", "zoomzoom-admin", "doc:repos", props={"stack": "php", "tier": "legacy", "status": "active"}))
    col.node(node_rec("db:zzt", "Database", "zzt", "schema@1", props={"handle": "zzt"}))
    for table, cols in {"zoom_order": [("order_id", True), ("order_status_id", False)],
                        "zoom_order_product": [("order_product_id", True), ("order_id", False)],
                        "zoom_ms_requestpayment": [("id", True), ("order_id", False)]}.items():
        col.node(node_rec(model.table_uid(table), "Table", table, "schema@1", props={"db": "zzt"}))
        for c, pk in cols:
            col.node(node_rec(model.col_uid(table, c), "Column", c, "schema@1", props={"type": "int", "nullable": False, "isPk": pk}))


def _run() -> Collector:
    col = Collector()
    _seed(col)
    php.extract(col, [php.RepoSpec(REPO, FIX / REPO, php.AREAS[REPO])])
    php.ensure_placeholders(col)
    return col


def _edges(col: Collector, etype: str, frm: str | None = None, to: str | None = None):
    return [rec for (f, t, o), rec in col.edges.items() if t == etype and (frm is None or f == frm) and (to is None or o == to)]


U = {
    "cls": model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo"),
    "update": model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo", "updateStatus"),
    "get": model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo", "getOrder"),
    "copy": model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo", "copyRequest"),
    "log": model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo", "log"),
    "status": model.code_uid(REPO, "admin/controller/cron/tasks.php", "ControllerCronTasks", "statusCheck"),
}


def test_tokenizer_skips_comments_strings_and_heredoc():
    src = "<?php\n// SELECT not code\n$a = 'it\\'s'; $b = \"x\\\"y\"; $c = <<<EOT\nSELECT 1\nEOT;\n/* UPDATE */ function f() {}\n"
    toks = phplex.tokenize(src)
    kinds = [(t.kind, t.text) for t in toks if t.kind in ("str", "ident")]
    assert ("str", "it's") in kinds and ("str", 'x"y') in kinds and ("str", "SELECT 1") in kinds
    assert ("ident", "function") in kinds and not any(t.text.startswith("//") for t in toks)
    fs = phplex.parse(toks)
    assert [f.name for f in fs.functions] == ["f"]


def test_sqlshape_ops_joins_and_dynamic():
    s = sqlshape.shape("SELECT o.* FROM zoom_order o LEFT JOIN zoom_order_product op ON o.order_id = op.order_id WHERE 1")
    assert s.tables == {"zoom_order": {"select"}, "zoom_order_product": {"select"}}
    assert s.joins == {("zoom_order", "zoom_order_product")}
    assert s.on_pairs == [(("zoom_order", "order_id"), ("zoom_order_product", "order_id"))]
    s = sqlshape.shape("INSERT INTO zoom_a (x) SELECT x FROM zoom_b")
    assert s.tables == {"zoom_a": {"insert"}, "zoom_b": {"select"}}
    assert sqlshape.shape("UPDATE zoom_a a JOIN zoom_b b ON a.id=b.a_id SET a.x = 1").tables == {"zoom_a": {"update"}, "zoom_b": {"select"}}
    assert sqlshape.shape("DELETE FROM zoom_a WHERE id = ?").tables == {"zoom_a": {"delete"}}
    assert sqlshape.shape("SELECT 1 FROM  ?  WHERE 1").dynamic and sqlshape.shape("SHOW VARIABLES LIKE 'x'").tables == {}
    assert sqlshape.shape("TRUNCATE TABLE zoom_a").tables == {"zoom_a": {"truncate"}}
    s = sqlshape.shape("SELECT c.id FROM zoom_coupon c JOIN zoom_coupon_ ? cd ON c.coupon_id = cd.coupon_id")
    assert s.tables == {"zoom_coupon": {"select"}} and s.dynamic
    assert sqlshape.shape("just text").stmt is None


def test_files_units_and_denied_paths():
    col = _run()
    files = {u for u in col.nodes if u.startswith("file:")}
    assert model.file_uid(REPO, "system/library/zoomtu/order_info.php") in files
    assert not any("scripts/dump.php" in u for u in files)           # deny_paths
    cls = col.nodes[U["cls"]]
    assert cls["props"]["kind"] == "class" and cls["props"]["parent"] == "Model" and cls["props"]["lineStart"] == 5
    assert cls["props"]["staticArrays"] == {"order_status_string": {"1": "book_requested", "2": "book_confirmed"}}   # secretMap 제외
    assert col.nodes[U["update"]]["props"] == {"kind": "method", "lineStart": 13, "lineEnd": 18, "visibility": "public", "class": "ZZTOrderInfo"}
    assert col.nodes[U["log"]]["props"]["visibility"] == "private"
    assert col.nodes[model.code_uid(REPO, "admin/controller/cron/tasks.php", "ControllerCronTasks")]["props"]["kind"] == "controller"
    assert col.nodes[model.code_uid(REPO, "admin/model/sale/order.php", "ModelSaleOrder")]["props"]["kind"] == "model"
    assert "module:zoomzoom-admin/system/library/zoomtu" in col.nodes and "module:zoomzoom-admin/admin/controller" in col.nodes


def test_reads_writes_joins_references():
    col = _run()
    (w,) = _edges(col, "WRITES", U["update"])
    assert w["to"] == "table:zoom_order" and w["props"] == {"ops": ["update"], "lines": [16], "handle": "db"}
    reads = {e["to"]: e["props"] for e in _edges(col, "READS", U["get"])}
    assert set(reads) == {"table:zoom_order", "table:zoom_order_product"} and reads["table:zoom_order"]["handle"] == "read_db"
    (j,) = _edges(col, "JOINS", "table:zoom_order", "table:zoom_order_product")
    assert j["props"]["count"] == 1 and j["props"]["onColumns"] == ["zoom_order.order_id=zoom_order_product.order_id"]
    (r,) = [e for e in _edges(col, "REFERENCES") if e["props"].get("kind") == "logical"]
    assert (r["from"], r["to"]) == ("col:zoom_order_product.order_id", "col:zoom_order.order_id")       # FK → PK 방향
    # INSERT … SELECT, 다른 DB 핸들, 스키마에 없는 테이블, 동적 테이블명
    copy_w = {e["to"]: e["props"]["ops"] for e in _edges(col, "WRITES", U["copy"])}
    copy_r = {e["to"]: e["props"]["handle"] for e in _edges(col, "READS", U["copy"])}
    assert copy_w == {"table:zoom_ms_requestpayment": ["insert"]}
    assert copy_r == {"table:zoom_order": "db", "table:stats/zoom_stats_data": "stats_db"}
    assert col.nodes["db:stats"]["label"] == "Database" and col.nodes["table:stats/zoom_stats_data"]["props"]["db"] == "stats"
    assert not any("ghost" in to for (_, _, to) in col.edges)
    report = "\n".join(col.sections["php"])
    assert "zoom_ghost_table" in report and "order_info.php:38" in report      # 동적 테이블명 줄


def test_calls_routes_enums_publishes_and_placeholders():
    col = _run()
    calls = {e["to"]: e["props"]["kind"] for e in _edges(col, "CALLS", U["get"])}
    assert calls == {model.code_uid(REPO, "system/library/zoomtu/commission.php", "ZZTCommissionBase", "commissionInfoFromOrder"): "zoomtu",
                     U["log"]: "self"}                                        # 부모 클래스 메서드로 해석, nope() 는 관계 없음
    calc = model.code_uid(REPO, "system/library/zoomtu/commission.php", "ZZTCommission", "calc")
    assert {e["to"] for e in _edges(col, "CALLS", calc)} == {model.code_uid(REPO, "system/library/zoomtu/commission.php", "ZZTCommission", "helper")}
    sc = {e["to"]: e["props"]["kind"] for e in _edges(col, "CALLS", U["status"])}
    missing = model.code_uid(REPO, "system/library/zoomtu/order_info.php", "ZZTOrderInfo", "missingMethod")
    assert sc == {U["update"]: "zoomtu", missing: "zoomtu",
                  model.code_uid(REPO, "admin/model/sale/order.php", "ModelSaleOrder", "getTotal"): "model",
                  model.code_uid(REPO, "admin/controller/common/header.php", "ControllerCommonHeader", "index"): "controller"}
    assert col.nodes[missing]["status"] == "missing-from-source" and col.nodes[missing]["props"]["placeholder"] is True
    routes = {u for u in col.nodes if u.startswith("route:")}
    assert routes == {"route:zoomzoom-admin route=cron/tasks/statuscheck", "route:zoomzoom-admin route=cron/tasks/index",
                      "route:zoomzoom-admin route=cron/tasks", "route:zoomzoom-admin route=common/header/index",
                      "route:zoomzoom-admin route=common/header"}
    assert _edges(col, "HANDLES", U["status"])[0]["to"] == "route:zoomzoom-admin route=cron/tasks/statuscheck"
    e1 = col.nodes["enum:zoom_order.order_status_id=1"]
    assert e1["props"]["origin"] == "code-static-array" and e1["props"]["meaning"] == "book_requested"
    assert _edges(col, "DEFINES", U["cls"], "enum:zoom_order.order_status_id=1") and _edges(col, "HAS_VALUE", "col:zoom_order.order_status_id")
    (p,) = _edges(col, "PUBLISHES", U["status"])
    assert p["to"] == "msg:order/confirm-order" and col.nodes["queue:order"]["props"]["role"] == "order"


def test_output_has_no_sql_text_and_passes_schema():
    col = _run()
    dumped = json.dumps(list(col.nodes.values()) + list(col.edges.values()), ensure_ascii=False)
    assert "WHERE" not in dumped and "SELECT" not in dumped and "supersecret" not in dumped and "abcdef123456" not in dumped
    schema = Schema.load()
    nodes = list(col.nodes.values())
    edges = [rec for (f, _, t), rec in col.edges.items() if f in col.nodes and t in col.nodes]
    for rec in nodes + edges:
        rec["firstSeenAt"] = rec["lastSeenAt"] = "2026-10-28"
    assert schema.check_bundle(nodes, edges) == []
    assert len(edges) == len(col.edges)          # fixture 안에서는 dangling 이 없어야 한다
