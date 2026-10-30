"""ts 추출기 — tests/fixtures/ts 의 작은 TS 저장소 4개를 node(ts-morph)로 돌리고 Python 쪽 병합·저장소 간 해석을 고정한다."""

import json
import shutil
from pathlib import Path

import pytest

from zoomtology import model, php, ts
from zoomtology.collect import Collector, node_rec
from zoomtology.schema import Schema

FIX = Path(__file__).parent / "fixtures" / "ts"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")


def _seed(col: Collector) -> None:
    for repo in ("zoomzoom-api", "message-consumer", "zoomzoom-back", "zoomzoom-front"):
        col.node(node_rec(f"repo:{repo}", "Repo", repo, "doc:repos", props={"stack": "ts", "tier": "new", "status": "active"}))
    for table, cols in {"zoom_order": ["order_id", "order_status_id"], "zoom_order_product": ["order_product_id", "order_id"]}.items():
        col.node(node_rec(model.table_uid(table), "Table", table, "schema@1", props={"db": "zzt"}))
        for c in cols:
            col.node(node_rec(model.col_uid(table, c), "Column", c, "schema@1", props={"type": "int", "nullable": False, "isPk": c.endswith("_id") and c.startswith(table[5:])}))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("ts")
    col = Collector()
    _seed(col)
    repos = [ts.TsRepo(name, FIX / name) for name in ("zoomzoom-api", "message-consumer", "zoomzoom-back", "zoomzoom-front")]
    meta = ts.extract(col, repos, out_dir=out_dir)
    php.ensure_placeholders(col)
    return col, meta


def _edges(col, etype, frm=None, to=None):
    return [rec for (f, t, o), rec in col.edges.items() if t == etype and (frm is None or f == frm) and (to is None or o == to)]


API = "zoomzoom-api"
U = {
    "repo_confirm": model.code_uid(API, "src/order/order.repository.ts", "OrderRepository", "confirm"),
    "repo_find": model.code_uid(API, "src/order/order.repository.ts", "OrderRepository", "findWithProducts"),
    "svc_confirm": model.code_uid(API, "src/order/order.service.ts", "OrderService", "confirm"),
    "ctrl": model.code_uid(API, "src/order/order.controller.ts", "OrderController", "confirmed"),
    "handler": model.code_uid(API, "src/order/confirm-order.handler.ts", "ConfirmOrderHandler", "execute"),
    "consumer": model.code_uid("message-consumer", "src/services/sqs/confirm-order.ts", "ConfirmOrderService", "execute"),
}


def test_entities_and_repository_access(built):
    col, meta = built
    assert meta["zoomzoom-api"].startswith("files=")
    ent = col.nodes[model.code_uid(API, "src/entities/order.entity.ts", "OrderEntity")]
    assert ent["props"]["kind"] == "entity" and ent["props"]["table"] == "zoom_order" and "order_status_id" in ent["props"]["columns"]
    assert _edges(col, "MAPS_TO", ent["uid"], "table:zoom_order")
    w = {e["to"]: e["props"] for e in _edges(col, "WRITES", U["repo_confirm"])}
    r = {e["to"]: e["props"] for e in _edges(col, "READS", U["repo_confirm"])}
    assert w["table:zoom_order"]["ops"] == ["update"]                     # import 별칭(OrderEntity as Order) 해석
    assert w["table:zoom_order_product"]["ops"] == ["upsert"]             # dataSource.manager.save(products) 타입 해석
    assert r["table:zoom_order_product"]["handle"] in ("typeorm", "raw-sql") and "select" in r["table:zoom_order_product"]["ops"]
    jr = {e["to"] for e in _edges(col, "READS", U["repo_find"])}
    assert jr == {"table:zoom_order", "table:zoom_order_product"}         # createQueryBuilder('o').innerJoinAndSelect('o.products')
    cw = {e["to"]: e["props"]["ops"] for e in _edges(col, "WRITES", model.code_uid(API, "src/order/order.repository.ts", "OrderRepository", "createWithProducts"))}
    assert cw == {"table:zoom_order": ["upsert"], "table:zoom_order_product": ["cascade:upsert"]}   # cascade: true 전파


def test_routes_calls_cqrs_publishes(built):
    col, _ = built
    assert "route:zoomzoom-api PATCH /order/:id/confirmed" in col.nodes and "route:zoomzoom-api GET /order/:id" in col.nodes
    assert col.nodes["route:zoomzoom-api POST /task/order/expire"]["props"]["kind"] == "task"
    assert _edges(col, "HANDLES", U["ctrl"], "route:zoomzoom-api PATCH /order/:id/confirmed")
    calls = {e["to"]: e["props"]["kind"] for e in _edges(col, "CALLS", U["svc_confirm"])}
    assert calls[U["repo_confirm"]] == "di" and calls[U["handler"]] == "cqrs"
    assert calls[model.code_uid(API, "src/order/order.service.ts", "OrderService", "notify")] == "self"
    (p,) = _edges(col, "PUBLISHES", U["svc_confirm"])
    assert p["to"] == "msg:order/confirm-order" and col.nodes["queue:order"]["props"]["consumerService"] == "svc:message-consumer/order"


def test_consumer_back_front_resolution(built):
    col, _ = built
    (c,) = _edges(col, "CONSUMES", U["consumer"])
    assert c["to"] == "msg:order/confirm-order"
    http = {e["to"]: e["props"] for e in _edges(col, "CALLS_HTTP", U["consumer"])}
    rule = "route:zoomzoom-back PATCH ^order/[0-9]+/confirmed$"
    assert rule in http and http[rule]["via"] == "accessrule"
    ph = "route:zoomzoom-back GET /zoomzoom/nothing/:param"              # 중첩 템플릿도 경로로, 규칙 없으면 placeholder
    assert ph in http and col.nodes[ph]["status"] == "missing-from-source"
    api = {e["to"]: e["props"]["matchKind"] for e in _edges(col, "CALLS_HTTP", rule)}
    assert api == {"route:zoomzoom-api PATCH /order/:id/confirmed": "regex"}      # `[0-9]+` 가 있어 regex
    prefix = {e["to"] for e in _edges(col, "CALLS_HTTP", "route:zoomzoom-back GET ^order/")}
    assert prefix == {"route:zoomzoom-api GET /order/:id"}
    front = model.code_uid("zoomzoom-front", "src/apis/order.ts", "confirmOrder")
    assert {e["to"] for e in _edges(col, "CALLS_HTTP", front)} == {rule}
    assert {e["to"] for e in _edges(col, "CALLS_HTTP", model.code_uid("zoomzoom-front", "src/apis/order.ts", "fetchOrder"))} == {"route:zoomzoom-back GET ^order/"}
    assert "svc:zoomzoom-api/mq" in col.nodes and "svc:message-consumer/order" in col.nodes
    assert _edges(col, "CONTAINS", "svc:zoomzoom-api/mq", "module:zoomzoom-api/src/task")


def test_no_code_text_and_schema_ok(built):
    col, _ = built
    dumped = json.dumps(list(col.nodes.values()) + list(col.edges.values()), ensure_ascii=False)
    assert "SELECT COUNT" not in dumped and "process.env" not in dumped
    schema = Schema.load()
    nodes = list(col.nodes.values())
    edges = [rec for (f, _, t), rec in col.edges.items() if f in col.nodes and t in col.nodes]
    for rec in nodes + edges:
        rec["firstSeenAt"] = rec["lastSeenAt"] = "2026-10-28"
    assert schema.check_bundle(nodes, edges) == []
    assert len(edges) == len(col.edges)
