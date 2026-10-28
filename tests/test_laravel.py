"""laravel 추출기 — 작은 fixture 저장소(tests/fixtures/laravel/zoomzoom-auth)로 핵심 동작을 고정한다."""

import json
from pathlib import Path

from zoomtology import laravel, model
from zoomtology.collect import Collector, node_rec
from zoomtology.schema import Schema

FIX = Path(__file__).parent / "fixtures" / "laravel"
REPO = "zoomzoom-auth"


def _seed(col: Collector) -> None:
    col.node(node_rec("repo:zoomzoom-auth", "Repo", "zoomzoom-auth", "doc:repos", props={"stack": "laravel", "tier": "legacy", "status": "active"}))
    col.node(node_rec("db:zzt", "Database", "zzt", "schema@1", props={"handle": "zzt"}))
    for table, cols in {"zoom_transactions": ["id", "reference_id", "revenue"], "zoom_order": ["order_id"],
                        "zoom_ms_commission": ["commission_id"], "provider_product": ["provider_id"]}.items():
        col.node(node_rec(model.table_uid(table), "Table", table, "schema@1", props={"db": "zzt"}))
        for c in cols:
            col.node(node_rec(model.col_uid(table, c), "Column", c, "schema@1", props={"type": "int", "nullable": False, "isPk": c in ("id", "order_id")}))


def _run() -> Collector:
    col = Collector()
    _seed(col)
    laravel.extract(col, laravel.LaravelRepo(REPO, FIX / REPO))
    return col


def _edges(col: Collector, etype: str, frm: str | None = None, to: str | None = None):
    return [rec for (f, t, o), rec in col.edges.items() if t == etype and (frm is None or f == frm) and (to is None or o == to)]


U = {
    "tx": model.code_uid(REPO, "app/Entities/Transaction.php", "Transaction"),
    "pp": model.code_uid(REPO, "app/Entities/ProviderProduct.php", "ProviderProduct"),
    "ghost": model.code_uid(REPO, "app/Entities/Ghost.php", "Ghost"),
    "cmd": model.code_uid(REPO, "app/Console/Commands/Crons/LockScheduledPayout.php", "LockScheduledPayout"),
    "handle": model.code_uid(REPO, "app/Console/Commands/Crons/LockScheduledPayout.php", "LockScheduledPayout", "handle"),
    "svc_get": model.code_uid(REPO, "app/Services/BatchPayoutScheduleService.php", "BatchPayoutScheduleService", "getSchedulesByStatus"),
    "svc_missing": model.code_uid(REPO, "app/Services/BatchPayoutScheduleService.php", "BatchPayoutScheduleService", "missingMethod"),
    "svc_filter": model.code_uid(REPO, "app/Services/BatchPayoutScheduleService.php", "BatchPayoutScheduleService", "filter"),
    "svc_di": model.code_uid(REPO, "app/Services/BatchPayoutScheduleService.php", "BatchPayoutScheduleService", "viaDi"),
    "ctl_add": model.code_uid(REPO, "app/Http/Controllers/V1/WishlistController.php", "WishlistController", "add"),
    "ctl_show": model.code_uid(REPO, "app/Http/Controllers/V1/WishlistController.php", "WishlistController", "show"),
}


def test_files_modules_kinds_and_denied_paths():
    col = _run()
    files = {u for u in col.nodes if u.startswith("file:")}
    assert model.file_uid(REPO, "app/Console/Kernel.php") in files and model.file_uid(REPO, "routes/api/v1/wishlist.php") in files
    assert not any("config/" in u for u in files)
    assert {"module:zoomzoom-auth/app/Entities", "module:zoomzoom-auth/app/Console/Commands", "module:zoomzoom-auth/app/Http/Controllers",
            "module:zoomzoom-auth/app/Services", "module:zoomzoom-auth/app/Console", "module:zoomzoom-auth/routes"} <= {u for u in col.nodes if u.startswith("module:")}
    assert col.nodes["module:zoomzoom-auth/app/Entities"]["props"]["kind"] == "laravel-app"
    assert col.nodes[U["tx"]]["props"]["kind"] == "model" and col.nodes[U["cmd"]]["props"]["kind"] == "command"
    assert col.nodes[model.code_uid(REPO, "app/Http/Controllers/V1/WishlistController.php", "WishlistController")]["props"]["kind"] == "controller"
    assert col.nodes[U["cmd"]]["props"]["signature"] == "zzt-cron:lock-scheduled-payout"
    assert col.nodes[U["cmd"]]["props"]["signatureFull"] == "zzt-cron:lock-scheduled-payout {--dry}"
    assert col.nodes[U["tx"]]["props"]["namespace"] == "App\\Entities" and col.nodes[U["tx"]]["props"]["parent"] == "ZZTBaseEntiry"
    assert col.nodes[U["handle"]]["props"] == {"kind": "method", "lineStart": 12, "lineEnd": 20, "visibility": "public", "class": "LockScheduledPayout"}


def test_models_map_to_tables_with_prefix_and_columns():
    col = _run()
    (m,) = _edges(col, "MAPS_TO", U["tx"])
    assert m["to"] == "table:zoom_transactions" and m["props"] == {"via": "eloquent-table"}
    assert col.nodes[U["tx"]]["props"]["table"] == "transactions" and col.nodes[U["tx"]]["props"]["columns"] == ["revenue"]
    (p,) = _edges(col, "MAPS_TO", U["pp"])
    assert p["to"] == "table:provider_product" and col.nodes[U["pp"]]["props"]["connection"] == "mysql_without_prefix"
    assert _edges(col, "MAPS_TO", U["ghost"]) == []
    report = "\n".join(col.sections["laravel"])
    assert "`App\\Entities\\Ghost`" in report and "`zoom_transactions.nope_col`" in report


def test_kernel_schedule_cronjob_triggers_and_flags():
    col = _run()
    lock = col.nodes["cron:zoomzoom-auth/lock-scheduled-payout"]
    assert lock["label"] == "CronJob" and lock["props"]["schedule"] == "timezone(Asia/Seoul) weeklyOn(2)"
    assert lock["props"]["host"] == "sf" and lock["props"]["runner"] == "laravel-schedule" and lock["props"]["kernelLine"] == 29
    assert lock["props"]["signature"] == "zzt-cron:lock-scheduled-payout" and lock["props"]["target"] == U["handle"]
    (t,) = _edges(col, "TRIGGERS", "cron:zoomzoom-auth/lock-scheduled-payout")
    assert t["to"] == U["handle"] and t["props"]["schedule"] == "timezone(Asia/Seoul) weeklyOn(2)"
    mil = col.nodes["cron:zoomzoom-auth/confim-mileage"]
    assert mil["props"]["enabledFlag"] == "zzt.cron.enabled.confirm_mileage" and mil["props"]["schedule"] == "timezone(Asia/Seoul) dailyAt(04:50)"
    assert _edges(col, "TRIGGERS", "cron:zoomzoom-auth/confim-mileage") == []        # 명령 클래스 없음 → report
    assert "cron:zoomzoom-auth/ghost" not in col.nodes                                  # 주석 처리된 호출
    assert "zzt-cron:confim-mileage" in "\n".join(col.sections["laravel"])


def test_reads_writes_from_db_facade_and_eloquent():
    col = _run()
    w = {e["to"]: e["props"] for e in _edges(col, "WRITES", U["handle"])}
    assert w == {"table:zoom_transactions": {"ops": ["update"], "lines": [16], "handle": "eloquent"}}
    r = {e["to"]: e["props"] for e in _edges(col, "READS", U["handle"])}
    assert r == {"table:zoom_transactions": {"ops": ["select"], "lines": [17], "handle": "eloquent"}}      # truncate 는 주석
    r = {e["to"]: e["props"] for e in _edges(col, "READS", U["svc_get"])}
    assert r["table:zoom_order"] == {"ops": ["select"], "lines": [21, 23], "handle": "db"}               # DB::select + 'order as o'
    assert r["table:zoom_transactions"]["handle"] == "db" and r["table:provider_product"] == {"ops": ["select"], "lines": [24], "handle": "eloquent"}
    w = {e["to"]: e["props"] for e in _edges(col, "WRITES", U["svc_get"])}
    assert w == {"table:zoom_ms_commission": {"ops": ["delete"], "lines": [22], "handle": "db"}}
    (c,) = _edges(col, "WRITES", U["ctl_add"])
    assert c["to"] == "table:zoom_transactions" and c["props"]["ops"] == ["insert"]


def test_calls_static_self_di_and_placeholders():
    col = _run()
    calls = {e["to"]: e["props"]["kind"] for e in _edges(col, "CALLS", U["handle"])}
    assert calls == {U["svc_get"]: "static", U["svc_missing"]: "static"}
    assert col.nodes[U["svc_missing"]]["status"] == "missing-from-source" and col.nodes[U["svc_missing"]]["props"]["placeholder"] is True
    assert {e["to"]: e["props"]["kind"] for e in _edges(col, "CALLS", U["svc_get"])} == {U["svc_filter"]: "self"}
    assert _edges(col, "CALLS", U["svc_di"]) == []
    assert "`OrderRepository`" in "\n".join(col.sections["laravel"])


def test_routes_prefix_and_handles():
    col = _run()
    routes = {u for u in col.nodes if u.startswith("route:")}
    assert routes == {"route:zoomzoom-auth POST /v1/wishlist", "route:zoomzoom-auth GET /v1/wishlist/{id}", "route:zoomzoom-auth DELETE /v1/wishlist/{id}"}
    r = col.nodes["route:zoomzoom-auth POST /v1/wishlist"]
    assert r["props"] == {"repo": REPO, "kind": "http", "method": "POST", "path": "/v1/wishlist", "file": "routes/api/v1/wishlist.php"}
    assert _edges(col, "HANDLES", U["ctl_add"])[0]["to"] == "route:zoomzoom-auth POST /v1/wishlist"
    assert _edges(col, "HANDLES", U["ctl_show"])[0]["to"] == "route:zoomzoom-auth GET /v1/wishlist/{id}"
    assert col.nodes[U["ctl_show"]]["status"] == "missing-from-source"
    assert "NopeController@delete" in "\n".join(col.sections["laravel"])
    assert _edges(col, "HANDLES", to="route:zoomzoom-auth DELETE /v1/wishlist/{id}") == []


def test_output_has_no_sql_text_and_passes_schema():
    col = _run()
    dumped = json.dumps(list(col.nodes.values()) + list(col.edges.values()), ensure_ascii=False)
    assert "SELECT" not in dumped and "WHERE" not in dumped and "supersecret" not in dumped
    schema = Schema.load()
    nodes = list(col.nodes.values())
    edges = [rec for (f, _, t), rec in col.edges.items() if f in col.nodes and t in col.nodes]
    for rec in nodes + edges:
        rec["firstSeenAt"] = rec["lastSeenAt"] = "2026-10-28"
    assert schema.check_bundle(nodes, edges) == []
    assert len(edges) == len(col.edges)
