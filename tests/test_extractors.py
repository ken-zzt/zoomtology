"""schema_ddl·docs·collect 의 핵심 동작을 작은 fixture 로 고정한다."""

from pathlib import Path

from zoomtology import docs, model, schema_ddl
from zoomtology.collect import Collector, node_rec

FIX = Path(__file__).parent / "fixtures"


def test_parse_dump_columns_pk_fk_comment():
    t = schema_ddl.parse_dump(FIX / "ddl.sql")
    assert set(t) == {"zoom_order", "zoom_seller_charge"}
    o = t["zoom_order"]
    assert o.comment == "주문" and o.engine == "InnoDB"
    assert [c.name for c in o.columns] == ["order_id", "product_id", "order_status_id", "note_status", "status", "secret"]
    assert o.columns[0].is_pk and o.columns[0].type == "int" and not o.columns[0].nullable
    assert o.columns[3].nullable and o.columns[3].type == "tinyint"
    assert t["zoom_seller_charge"].fks == [("seller_id", "zoom_ms_seller", "seller_id", "zoom_seller_charge_ibfk_1")]


def test_enum_from_comment_pairs_and_lists():
    assert schema_ddl.enum_from_comment("노트 상태 - 0: Open, 1: Closed", "tinyint") == [("0", "Open"), ("1", "Closed")]
    assert schema_ddl.enum_from_comment("pending, recording, canceled", "varchar(20)") == [("pending", None), ("recording", None), ("canceled", None)]
    assert schema_ddl.enum_from_comment("pending, recording, canceled", "int") == []
    assert schema_ddl.enum_from_comment("zoom_transactions.id (kind=seller_charge)", "int") == []
    assert schema_ddl.enum_from_comment(None, "int") == []


def test_schema_extract_never_stores_defaults_or_sql():
    col = Collector()
    schema_ddl.extract(col, FIX / "ddl.sql", None)
    secret = col.nodes[model.col_uid("zoom_order", "secret")]
    assert "default" not in secret["props"]
    dumped = str(col.nodes) + str(col.edges)
    assert "sk_live" not in dumped and "CREATE TABLE" not in dumped
    assert (model.col_uid("zoom_seller_charge", "seller_id"), "REFERENCES", model.col_uid("zoom_ms_seller", "seller_id")) in col.edges
    assert col.nodes[model.enum_uid("zoom_order", "note_status", "1")]["props"]["meaning"] == "Closed"


def test_status_codes_parsing(monkeypatch):
    monkeypatch.setattr(docs, "HUB", FIX / "docs" / "hub")
    hub = FIX / "docs" / "hub" / "docs" / "20-database"
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "status-codes.md").write_text((FIX / "docs" / "status-codes.md").read_text(encoding="utf-8"), encoding="utf-8")
    col = Collector()
    n = docs.extract_status_codes(col)
    assert n == 2 + 2 + 1
    v1 = col.nodes[model.enum_uid("zoom_order", "order_status_id", "1")]
    assert v1["props"]["meaning"] == "예약요청"          # bold 제거
    card = col.nodes[model.enum_uid("zoom_ms_requestpayment", "payment_type", "card")]
    assert card["props"]["label"] == "카드" and card["props"]["meaning"] == "카드 결제"
    kind = col.nodes[model.enum_uid("zoom_transactions", "kind", "seller_charge")]
    assert kind["props"]["origin"] == "status-codes"
    assert (model.col_uid("zoom_order", "order_status_id"), "HAS_VALUE", v1["uid"]) in col.edges


def test_collector_precedence_doc_over_extractor_keeps_creator_source():
    col = Collector()
    col.node(node_rec("table:zoom_order", "Table", "zoom_order", "schema@1", summary="DDL comment", props={"db": "zzt"}, source_ref="dump:zoom_order"))
    col.node(node_rec("table:zoom_order", "Table", "zoom_order", "doc:x.md", summary="문서 설명", props={"aliases": ["주문"]}, source_ref="x.md"), partial=True)
    n = col.nodes["table:zoom_order"]
    assert n["summary"] == "문서 설명"
    assert n["source"] == "schema@1" and n["sourceRef"] == "dump:zoom_order"
    assert n["props"]["alt"]["schema@1"]["summary"] == "DDL comment"
    assert n["props"]["aliases"] == ["주문"] and n["props"]["docRefs"] == ["x.md"]


def test_collector_partial_without_node_is_dropped():
    col = Collector()
    col.node(node_rec("col:nope.x", "Column", "x", "doc:y.md", props={"meaning": "?"}), partial=True)
    assert "col:nope.x" not in col.nodes and col.dropped_partials == [("col:nope.x", "doc:y.md")]


def test_md_tables_and_clean_cell():
    text = "| 값 | 의미 |\n|---|---|\n| 1 | [표](../x.md) **참조** `t` |\n"
    (_, header, rows), = list(docs.md_tables(text))
    assert header == ["값", "의미"] and rows == [["1", "[표](../x.md) **참조** `t`"]]
    assert docs._clean_cell(rows[0][1]) == "표 참조 t"
