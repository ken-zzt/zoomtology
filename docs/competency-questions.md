---
type: guide
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - ontology/schema.yaml
tags: [zoomtology, competency-questions, tests]
related_to:
  - decisions/0007-first-slice-scope-and-pilot.md
---

# 역량 질문 (Competency Questions) — 파일럿 "주문→결제→취소/환불→정산"

온톨로지는 클래스 수가 아니라 **실제 질문에 답하는지**로 검증한다. 아래 20개는 1차 그래프의 완료 기준이자 회귀 테스트다.
`tests/cq/` 의 러너가 로컬 Prism MCP(HTTP)에 각 도구 호출을 던지고 "반드시 포함" uid 가 있는지 확인한다(정확히 같을 필요는 없다 — 추출기는 계속 좋아진다).

도구 이름은 Prism `kg_*`(1~3단계에서 구현). 기대값의 uid 는 [`ontology/uid.md`](../ontology/uid.md) 규칙.
**curated 의존** 표시가 있는 것은 4단계(ZDV-348) 전엔 실패가 정상이다.

| # | 질문 | 도구 호출 | 반드시 포함 | 단계 |
|---|---|---|---|---|
| 1 | `zoom_order` 를 쓰는(WRITE) 코드는 어디인가? | `kg_code_for_table {table:"zoom_order", op:"write"}` | `code:zoomzoom-admin/system/library/zoomtu/order_info.php#ZZTOrderInfo::updateStatus` 등 zoomtu 유닛, zoomzoom-api 의 order 리포지토리 유닛 | 2 |
| 2 | `zoom_ms_requestpayment.status_id` 값 7 은 무슨 뜻인가? | `kg_node {uid:"col:zoom_ms_requestpayment.status_id"}` | `enumValues` 에 status-codes.md 의 22개 값 | 1 |
| 3 | `zoom_order.order_status_id` 의 코드 정의 enum 은? | `kg_neighbors {uid:"col:zoom_order.order_status_id", types:["HAS_VALUE"]}` | `origin: code-static-array` 값들(`ZZTOrderInfo::$order_status_string`) | 2 |
| 4 | `zoom_transactions` 를 바꾸면 어떤 크론·라우트가 영향을 받나? | `kg_impact {uid:"table:zoom_transactions", depth:3}` | `cron:admin/cron/tasks/updateTransactionFee`, `cron:admin/cron/tasks/payoutEstimate`, `/order`·`/transaction` 계열 api 라우트 | 3 |
| 5 | 예약요청 자동거절은 어느 크론이 어떤 코드로 하나? | `kg_node {uid:"rule:auto-reject"}` → `kg_neighbors {direction:"in", types:["IMPLEMENTS_RULE"]}` | 해당 크론 라우트와 `ZZTOrderInfo` 유닛 | 4 (curated) |
| 6 | `confirm-order` 메시지는 누가 보내고 누가 받나? | `kg_neighbors {uid:"msg:order/confirm-order", types:["PUBLISHES","CONSUMES"]}` | zoomzoom-api 발행 유닛, message-consumer `ConfirmOrderService::execute` | 3 |
| 7 | 그 컨슈머는 어떤 API 를 부르고 그 API 는 어떤 테이블을 쓰나? | `kg_neighbors {uid:<consumer unit>, types:["CALLS_HTTP"]}` → `kg_tables_for_code {ref:<route handler>}` | `route:zoomzoom-api …` 하나와 `zoom_order` 포함 테이블 | 3 |
| 8 | `zoom_order` 와 가장 자주 JOIN 되는 테이블은? | `kg_code_for_table {table:"zoom_order", op:"join"}` | `joins[]` 에 `zoom_ms_order_product_data`, `zoom_order_product`, `zoom_ms_requestpayment` | 2 |
| 9 | 정산(settlement) 도메인에 속한 테이블 목록 | `kg_neighbors {uid:"domain:settlement", direction:"in", types:["BELONGS_TO_DOMAIN"], limit:100}` | `zoom_seller_charge`, payout 계열 | 4 (curated) |
| 10 | `zoom_seller_charge.status` 값과 의미 | `kg_node {uid:"col:zoom_seller_charge.status"}` | status-codes.md 의 값들 | 1 |
| 11 | `zoom_order.product_id` 는 어느 테이블을 가리키나? (FK 없음) | `kg_neighbors {uid:"col:zoom_order.product_id", types:["REFERENCES"]}` | `col:zoom_product.product_id`, `kind: logical`, `confidence: verified` | 4 (curated) |
| 12 | `payoutEstimate` 크론이 읽고 쓰는 테이블 | `kg_tables_for_code {ref:"code:zoomzoom-admin/admin/controller/cron/tasks.php#ControllerCronTasks::payoutEstimate"}` | callee 경유 포함 3개 이상 | 2 |
| 13 | `addTransactionV2` 는 아직 쓰이나? | `kg_node {uid:"code:zoomzoom-admin/system/library/zoomtu/transactions.php#ZZTTransactions::addTransactionV2"}` | `status: retired`, `SUPERSEDES` 관계, 호출자 관계도 retired | 4 (curated) |
| 14 | 부분환불 정책 문서는 어떤 코드를 근거로 하나? | `kg_neighbors {uid:"rule:partial-refund", direction:"in", types:["IMPLEMENTS_RULE"]}` | 정책 문서 `sources:` 의 파일/유닛 uid | 1 |
| 15 | 프런트의 주문 취소 요청은 어떤 경로로 API 까지 가나? | `kg_path {from:<back accessrule route>, to:"table:zoom_order", maxDepth:6}` | `route:zoomzoom-api PATCH /order/…` 를 지나 리포지토리 유닛까지 | 3 |
| 16 | 레거시 유저 웹(zoomzoom-admin/catalog)의 라우트는 폐기됐나? | `kg_search {q:"route=product/product", label:"Route"}` | admin/catalog 라우트 `status: retired`, partners 는 `active` | 4 (curated) |
| 17 | `stats_db` 로 읽는 테이블은? | `kg_neighbors {uid:"db:stats", types:["CONTAINS"], limit:200}` → `kg_code_for_table {table:"table:stats/zoom_stats_data"}` | `table:stats/*` 테이블과 `handle: stats_db` 인 READS/WRITES (`ZZTStats::addStatsData`) | 2 |
| 18 | 정산 관련 Doc 중 `last_verified` 가 오래된 것은? | `kg_search {q:"정산", label:"Doc"}` → `props.lastVerified` | 존재 확인(정렬은 클라이언트) | 1 |
| 19 | 이 번들은 언제 어떤 커밋으로 만들어졌나? | `kg_bundle_info {}` | `build/latest/manifest.json` 의 version/sha 와 일치 | 1 |
| 20 | `zoom_ms_requestpayment` 에 INSERT 하는 코드와 그 라우트 | `kg_code_for_table {table:"zoom_ms_requestpayment", op:"write"}` → `kg_impact` | PHP 체크아웃 경로 1개 이상 + api 라우트 1개 이상 | 2 |
| 23 | (회귀) `ZZTOrderInfo::updateStatus` 가 직접 쓰는 테이블 | `kg_tables_for_code {uid:"code:…#ZZTOrderInfo::updateStatus", depth:0}` | `table:zoom_order` · ops `update` · via direct | 2 |
| 24 | (회귀) api `ConfirmOrderCommand::execute` 가 피호출자를 거쳐 닿는 테이블 | `kg_tables_for_code {uid:"zoomzoom-api/…#ConfirmOrderCommand::execute", depth:2}` | `table:zoom_order`·`table:zoom_customer_mileages` via callee (컨트롤러→서비스→커맨드→리포지토리는 3단계) | 3 |
| 25 | (회귀) Laravel 스케줄 `confim-mileage` 가 실행하는 명령 클래스 | `kg_neighbors {uid:"cron:zoomzoom-auth/confim-mileage", types:["TRIGGERS"]}` | `app/Console/Commands/Crons/…::handle` | 3 |
| 26 | (회귀) MQ 서버의 zoomzoom-api 사본이 담당하는 모듈 | `kg_neighbors {uid:"svc:zoomzoom-api/mq", types:["CONTAINS"]}` | `module:zoomzoom-api/src/task` | 3 |

## 측정

| 지표 | 목표 |
|---|---|
| 20개 중 통과 | 4단계 끝에 20/20 |
| `sourceRef` 가 있는 답 | 95% 이상 |
| 파일럿 테이블의 READ/WRITE 유닛 연결 | 100% (또는 승인된 제외 목록) |
| `confidence: verified` 비율(파일럿 도메인) | 논리 FK·retired·도메인 소속 100% |
| 빌드·적재 가드에 걸린 SQL/시크릿 | 0 (걸리면 빌드 실패) |

좋은 답의 모양(O 보고서): "예. `zoom_order` 는 `ZZTOrderInfo::updateStatus` 가 WRITES(UPDATE) 하며, 그 유닛은 `route=cron/tasks/statusCheck` 를 HANDLES 하고, 그 라우트는 `cron:admin/cron/tasks/statusCheck`(*/10 * * * *) 가 TRIGGERS 한다. 근거: `order_info.php:131`." — 경로 + 출처가 있어야 한다.
