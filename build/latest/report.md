# 빌드 report — 20261028T0639Z-0462990-dirty

- builtAt: 2026-10-28T06:39:13+00:00  gitSha: 0462990 (dirty)
- inputs: {"schema": {"primary": "local_zzt-2026-10-28.sql (502 tables)", "secondary": "urimalo_zzt-2026-04-22.sql (517 tables)", "tables": "519"}, "classification": {"classified": "492", "excluded": "10"}, "docs": {"docs": "102", "statusCodeValues": "124", "domainColumns": "432", "policies": "8", "cronJobs": "59", "glossary": "14", "ownership": "27", "repos": "17"}, "php": {"zoomzoom-admin": "files=879 classes=906 units=8417 queries=5559", "zoomzoom-partners": "files=463 classes=487 units=4461 queries=2875"}, "ts": {"zoomzoom-api": "files=3198 nodes=10320 edges=15887 ms=2894", "message-consumer": "files=103 nodes=461 edges=458 ms=826", "zoomzoom-back": "files=27 nodes=389 edges=394 ms=734", "external-api": "files=452 nodes=1665 edges=2236 ms=253", "data-api": "files=43 nodes=131 edges=170 ms=230", "zoomzoom-front": "files=856 nodes=2306 edges=2307 ms=2960"}, "laravel": {"zoomzoom-auth": "files=634 classes=594 units=2136 models=154 schedules=33 routes=194"}, "placeholders": {"calls": "85"}}

## 건수

| 라벨 | 노드 |
|---|---|
| BusinessRule | 8 |
| CodeUnit | 24534 |
| Column | 4049 |
| CronJob | 55 |
| Database | 3 |
| Doc | 161 |
| EnumValue | 272 |
| File | 6765 |
| Module | 186 |
| Queue | 5 |
| QueueMessage | 79 |
| Repo | 17 |
| Route | 3696 |
| Service | 7 |
| Table | 527 |

| 관계 | 건수 |
|---|---|
| CALLS | 20281 |
| CALLS_HTTP | 521 |
| CONSUMES | 78 |
| CONTAINS | 31867 |
| DEFINES | 368 |
| DOCUMENTED_BY | 580 |
| HANDLES | 3533 |
| HAS_COLUMN | 4049 |
| HAS_VALUE | 272 |
| IMPLEMENTS_RULE | 97 |
| JOINS | 1172 |
| MAPS_TO | 358 |
| PUBLISHES | 73 |
| READS | 8148 |
| REFERENCES | 432 |
| TRIGGERS | 80 |
| WRITES | 3178 |

- 이번 빌드에 처음 보인 노드: 40364
- 지난 빌드엔 있었는데 사라진 uid: 11

### 사라진 uid (verified 는 tombstone 대상 — 4단계에서 처리)

- `cron:admin/cron/tasks/checkContinuouslyBlockedDays`
- `cron:admin/cron/tasks/confirmBatchPayoutBalance`
- `cron:admin/cron/tasks/emailTaskRun`
- `cron:admin/cron/tasks/payoutEstimate`
- `cron:admin/cron/tasks/payoutMarkDone`
- `cron:admin/cron/tasks/resetCampaignCredits`
- `cron:admin/cron/tasks/updateElasticSearchData`
- `cron:admin/cron/tasks/updateTransactionFee`
- `cron:admin/task/task/checkProviderOrderStatus`
- `cron:admin/task/task/rejectOrderAfterWeek`
- `cron:admin/task/task/runUpdateStats`

- status: {'active': 40049, 'missing-from-source': 315}

## 추출기 report — php

### zoomzoom-admin

- 파일 879 · 클래스 906 · 코드 유닛 8417 · `->query(` 5559건
- 테이블 자리를 못 찾은 쿼리: 204건 (헬퍼가 조립하는 SQL·SHOW/DESCRIBE — tree-sitter 업그레이드 판단 자료)
- 테이블 이름은 있는데 전부 스키마에 없는 쿼리: 289건 (폐기 테이블·결제 확장)
- 테이블 자리가 변수인 쿼리: 36건
- 클래스는 있는데 메서드가 없어 placeholder 를 가리킨 호출: 214건
- 큐 발행 role 별 건수: {'order': 3, 'notif': 1} · key 를 못 읽은 sendMessage: 1건

테이블 자리를 못 찾은 쿼리 (최대 40):

- `zoomzoom-admin/admin/controller/cron/tasks.php:2128`
- `zoomzoom-admin/admin/controller/extension/installer.php:396`
- `zoomzoom-admin/admin/controller/module/errorlogmanager.php:230`
- `zoomzoom-admin/admin/controller/module/errorlogmanager.php:462`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:825`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:826`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:855`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:856`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:884`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:885`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:913`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:914`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:948`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:949`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:978`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:979`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1038`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1039`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1067`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1068`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1099`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1100`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1130`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1131`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1161`
- `zoomzoom-admin/admin/controller/module/zztdatabase.php:1162`
- `zoomzoom-admin/admin/controller/simple_blog/install.php:37`
- `zoomzoom-admin/admin/model/affiliate/affiliate.php:274`
- `zoomzoom-admin/admin/model/affiliate/affiliate.php:292`
- `zoomzoom-admin/admin/model/fraud/fraudlabspro.php:4`
- `zoomzoom-admin/admin/model/fraud/maxmind.php:4`
- `zoomzoom-admin/admin/model/module/errorlogmanager.php:4`
- `zoomzoom-admin/admin/model/module/errorlogmanager.php:19`
- `zoomzoom-admin/admin/model/module/errorlogmanager.php:65`
- `zoomzoom-admin/admin/model/module/errorlogmanager.php:103`
- `zoomzoom-admin/admin/model/module/multimerch_badges.php:4`
- `zoomzoom-admin/admin/model/module/multimerch_badges.php:10`
- `zoomzoom-admin/admin/model/module/multimerch_badges.php:18`
- `zoomzoom-admin/admin/model/module/smshare.php:10`
- `zoomzoom-admin/admin/model/module/smshare_scar.php:6`

동적 테이블명 (최대 20):

- `zoomzoom-admin/admin/model/tool/backup.php:18`
- `zoomzoom-admin/admin/model/tool/backup.php:50`
- `zoomzoom-admin/catalog/controller/tool/batch.php:4016`
- `zoomzoom-admin/catalog/model/catalog/product.php:1386`
- `zoomzoom-admin/system/library/zoomtu/coupon.php:576`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:70`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:144`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:186`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:230`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:319`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:362`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:384`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:508`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:560`
- `zoomzoom-admin/system/library/zoomtu/product_image_description.php:587`
- `zoomzoom-admin/system/library/zoomtu/support_ticket.php:263`
- `zoomzoom-admin/system/library/zoomtu/support_ticket.php:286`
- `zoomzoom-admin/system/library/zoomtu/support_ticket.php:340`
- `zoomzoom-admin/system/library/zoomtu/support_ticket.php:360`
- `zoomzoom-admin/system/library/zoomtu/support_ticket.php:386`

키워드 자리에 왔지만 스키마에 없는 이름 (상위 30):

- `zoom_paypal_iframe_order_transaction`: 12
- `zoom_paypal_order_transaction`: 11
- `zoom_errorlog_manager`: 7
- `zoom_amazon_login_pay_order_transaction`: 7
- `zoom_order_amazon_report`: 6
- `zoom_amazon_login_pay_order`: 6
- `zoom_securetrading_pp_order`: 6
- `zoom_securetrading_ws_order`: 6
- `zoom_order_amazon`: 5
- `zoom_bluepay_hosted_order`: 5
- `zoom_bluepay_hosted_order_transaction`: 5
- `zoom_bluepay_redirect_order`: 5
- `zoom_bluepay_redirect_order_transaction`: 5
- `zoom_firstdata_remote_order`: 5
- `zoom_firstdata_remote_order_transaction`: 5
- `zoom_g2apay_order_transaction`: 5
- `zoom_globalpay_order`: 5
- `zoom_globalpay_remote_order`: 5
- `zoom_paypal_payflow_iframe_order_transaction`: 5
- `zoom_paypal_iframe_order`: 5
- `zoom_realex_order`: 5
- `zoom_realex_remote_order`: 5
- `zoom_sagepay_direct_order`: 5
- `zoom_sagepay_direct_order_transaction`: 5
- `zoom_sagepay_server_order`: 5
- `zoom_sagepay_server_order_transaction`: 5
- `zoom_securetrading_pp_order_transaction`: 5
- `zoom_securetrading_ws_order_transaction`: 5
- `zoom_worldpay_order_transaction`: 5
- `zoom_fraudlabspro`: 4

`->query(` 인데 DB 핸들이 아닌 수신자 (건수):

- `$liveDB`: 2
- `$crawlerDB`: 1

해석 못 한 load 대상 (상위 30):

- `model:model_payment_amazon_login_pay`: 19
- `model:model_checkout_order`: 2
- `model:model_sale_return`: 2
- `controller:api/partner_app/header`: 1

### zoomzoom-partners

- 파일 463 · 클래스 487 · 코드 유닛 4461 · `->query(` 2875건
- 테이블 자리를 못 찾은 쿼리: 91건 (헬퍼가 조립하는 SQL·SHOW/DESCRIBE — tree-sitter 업그레이드 판단 자료)
- 테이블 이름은 있는데 전부 스키마에 없는 쿼리: 302건 (폐기 테이블·결제 확장)
- 테이블 자리가 변수인 쿼리: 28건
- 클래스는 있는데 메서드가 없어 placeholder 를 가리킨 호출: 20건
- 큐 발행 role 별 건수: {'order': 5, 'notif': 1}

테이블 자리를 못 찾은 쿼리 (최대 40):

- `zoomzoom-partners/catalog/model/module/smshare_scar.php:264`
- `zoomzoom-partners/catalog/model/openbay/ebay_order.php:598`
- `zoomzoom-partners/catalog/model/openbay/ebay_product.php:12`
- `zoomzoom-partners/catalog/model/openbay/ebay_product.php:14`
- `zoomzoom-partners/catalog/model/openbay/etsy_order.php:81`
- `zoomzoom-partners/system/library/zoomtu/account.php:10`
- `zoomzoom-partners/system/library/zoomtu/account.php:26`
- `zoomzoom-partners/system/library/zoomtu/activity.php:197`
- `zoomzoom-partners/system/library/zoomtu/activity.php:213`
- `zoomzoom-partners/system/library/zoomtu/agent.php:25`
- `zoomzoom-partners/system/library/zoomtu/agent.php:38`
- `zoomzoom-partners/system/library/zoomtu/auth_identity.php:180`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:74`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:100`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:113`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:129`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:148`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:166`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:180`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:191`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:202`
- `zoomzoom-partners/system/library/zoomtu/customer_service.php:173`
- `zoomzoom-partners/system/library/zoomtu/file.php:494`
- `zoomzoom-partners/system/library/zoomtu/file.php:506`
- `zoomzoom-partners/system/library/zoomtu/giftcoupon.php:145`
- `zoomzoom-partners/system/library/zoomtu/keyword.php:146`
- `zoomzoom-partners/system/library/zoomtu/keyword.php:162`
- `zoomzoom-partners/system/library/zoomtu/keyword.php:177`
- `zoomzoom-partners/system/library/zoomtu/message.php:538`
- `zoomzoom-partners/system/library/zoomtu/navertour.php:522`
- `zoomzoom-partners/system/library/zoomtu/old_product.php:79`
- `zoomzoom-partners/system/library/zoomtu/old_product.php:345`
- `zoomzoom-partners/system/library/zoomtu/old_product.php:351`
- `zoomzoom-partners/system/library/zoomtu/payout.php:330`
- `zoomzoom-partners/system/library/zoomtu/payout.php:362`
- `zoomzoom-partners/system/library/zoomtu/payout.php:996`
- `zoomzoom-partners/system/library/zoomtu/places.php:1063`
- `zoomzoom-partners/system/library/zoomtu/places.php:1084`
- `zoomzoom-partners/system/library/zoomtu/places.php:1096`
- `zoomzoom-partners/system/library/zoomtu/places.php:1108`

동적 테이블명 (최대 20):

- `zoomzoom-partners/catalog/model/catalog/product.php:1654`
- `zoomzoom-partners/system/library/zoomtu/coupon.php:676`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:69`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:92`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:100`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:108`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:288`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:341`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:481`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:510`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:550`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:575`
- `zoomzoom-partners/system/library/zoomtu/product_image_description.php:616`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:232`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:287`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:315`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:318`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:346`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:497`
- `zoomzoom-partners/system/library/zoomtu/support_ticket.php:551`

키워드 자리에 왔지만 스키마에 없는 이름 (상위 30):

- `zoom_ebay_setting_option`: 22
- `zoom_ebay_listing`: 10
- `zoom_amazonus_product`: 8
- `zoom_ebay_transaction`: 8
- `zoom_product_option_variant`: 8
- `zoom_ebay_stock_reserve`: 8
- `zoom_amazon_product`: 7
- `zoom_securetrading_ws_order`: 7
- `zoom_amazon_product_link`: 6
- `zoom_amazonus_product_link`: 6
- `zoom_order_amazon`: 6
- `zoom_etsy_order`: 5
- `zoom_amazon_login_pay_order`: 5
- `zoom_sagepay_direct_card`: 5
- `zoom_sagepay_direct_order`: 5
- `zoom_ebay_store_category`: 5
- `zoom_etsy_listing`: 5
- `zoom_amazon_order`: 4
- `zoom_amazonus_order`: 4
- `zoom_ebay_order`: 4
- `zoom_firstdata_order`: 4
- `zoom_firstdata_card`: 4
- `zoom_paypal_order_transaction`: 4
- `zoom_sagepay_server_order`: 4
- `zoom_ebay_shipping`: 4
- `zoom_ebay_image_import`: 3
- `zoom_order_total_tax`: 3
- `zoom_amazon_login_pay_order_total_tax`: 3
- `zoom_amazon_login_pay_order_transaction`: 3
- `zoom_g2apay_order`: 3

해석 못 한 load 대상 (상위 30):

- `model:model_module_openstock`: 11
- `model:model_sale_customer`: 6
- `model:model_openbay_amazon`: 3
- `model:model_openbay_amazonus`: 3
- `model:model_sale_order`: 2


## 추출기 report — ts

### zoomzoom-api

- {'files': 3198, 'entities': 232, 'calls-placeholder': 54, 'routes': 310, 'publishes': 64, 'manager-call-unresolved': 7, 'qb-unresolved': 3}
- raw-query-no-table (2): `zoomzoom-api/src/apis/v1/services/subproduct.ts:141`, `zoomzoom-api/src/product/infra/persistence/orm/repositories/subproduct.repository.ts:539`
- cqrs-unresolved (1): `zoomzoom-api/src/cart/application/services/update-cart.service.ts:51`
- qb-unresolved-sites (3): `59:queryRunner.manager.getRepository.createQueryBuilder`, `82:queryRunner.manager.getRepository.createQueryBuilder`, `7:repo.createQueryBuilder`
- qb-join-unresolved (9): `'pcf.fiedType'`, `'pcf.preDefined'`, `'r.customer'`, `'r.partner'`, `'pp.detail'`, `'r.product'`, `'r.order'`, `'o.requestPayment'`, `'rp.comments'`

### message-consumer

- {'files': 103, 'entities': 0, 'routes': 1, 'consumes': 85, 'http-calls': 72}
- http-call-unparsed (8): `message-consumer/src/services/sqs/conversation/conversation-updated.ts:20`, `message-consumer/src/services/sqs/conversation/first-conversation-replied.ts:20`, `message-consumer/src/services/sqs/luxury-escape/patch-price.ts:21`, `message-consumer/src/services/sqs/order/patch-order-status.ts:24`, `message-consumer/src/services/sqs/product/patch-product-available-date.ts:21`, `message-consumer/src/services/sqs/product/product-score-updated.ts:21`, `message-consumer/src/services/sqs/review/review-reminder.ts:90`, `message-consumer/src/services/sqs/triptopaz/patch-tour.ts:21`

### zoomzoom-back

- {'files': 27, 'rules-admin': 17, 'rules-partner': 11, 'rules-zoomzoom': 259}

### external-api

- {'files': 452, 'entities': 0, 'routes': 168}
- http-call-unparsed (60): `external-api/src/apis/v1/services/airbridge.ts:18`, `external-api/src/apis/v1/services/api.ts:19`, `external-api/src/apis/v1/services/api.ts:34`, `external-api/src/apis/v1/services/api.ts:53`, `external-api/src/apis/v1/services/api.ts:70`, `external-api/src/apis/v1/services/bok.ts:99`, `external-api/src/apis/v1/services/channel-talk.ts:57`, `external-api/src/apis/v1/services/channel-talk.ts:75`, `external-api/src/apis/v1/services/channel-talk.ts:90`, `external-api/src/apis/v1/services/channel-talk.ts:101`, `external-api/src/apis/v1/services/google.ts:15`, `external-api/src/apis/v1/services/jejumobile.ts:30` …

### data-api

- {'files': 43, 'entities': 3, 'routes': 5}
- http-call-unparsed (2): `data-api/src/airbridge/services/export-airbridge.ts:64`, `data-api/src/airbridge/services/import-airbridge.ts:110`
- raw-query-no-table (1): `data-api/src/stat/repositories/partner-response-repository.ts:30`

### zoomzoom-front

- {'files': 856, 'http-calls': 105}
- front-call-unparsed (7): `zoomzoom-front/src/apis/help.ts:8`, `zoomzoom-front/src/apis/help.ts:17`, `zoomzoom-front/src/apis/help.ts:42`, `zoomzoom-front/src/apis/help.ts:54`, `zoomzoom-front/src/apis/user.ts:136`, `zoomzoom-front/src/apis/wishlist.ts:19`, `zoomzoom-front/src/apis/wishlist.ts:37`

### 저장소 간

- 스키마에 없는 테이블로 향한 READS/WRITES/MAPS_TO 버림: 18건 — `table:iso/customer`×7, `table:jtr_category`×6, `table:vehicle_image`×3, `table:wc/zzt_crawling_data`×2
- consumer/front → back AccessRule 해석: {'message-consumer': 44, 'external-api': 23, 'zoomzoom-front': 89} · 미해석(placeholder): 21
- AccessRule → zoomzoom-api 라우트: {'regex': 262, 'exact': 79, 'target': 3} · 짝 없는 규칙: 16

미해석 HTTP 호출 (최대 30):

- `POST /zoomzoom/bemyguest/booking/:param ← message-consumer/src/services/sqs/provider/bemyguest-booking.ts:12`
- `POST /zoomzoom/waug/booking/:param ← message-consumer/src/services/sqs/provider/waug-booking.ts:12`
- `PATCH /zoomzoom/task/translation/product ← message-consumer/src/services/sqs/translation/product-updated.ts:14`
- `POST /document/voucher/jejumobile ← message-consumer/src/services/sqs/voucher/jejumobile-voucher.ts:12`
- `POST /document/voucher/zoomzoom ← message-consumer/src/services/sqs/voucher/zoomzoom-voucher.ts:13`
- `POST /log/frontend ← zoomzoom-front/src/apis/actionlog.ts:7`
- `POST /v2/auth/signin ← zoomzoom-front/src/apis/authentication.ts:22`
- `POST /v2/auth/signup ← zoomzoom-front/src/apis/authentication.ts:69`
- `GET /v2/auth/token ← zoomzoom-front/src/apis/authentication.ts:194`
- `GET /v2/auth/:param ← zoomzoom-front/src/apis/authentication.ts:276`
- `POST /v2/auth/refresh ← zoomzoom-front/src/apis/authentication.ts:381`
- `POST /zoomzoom/payment ← zoomzoom-front/src/apis/checkout.ts:113`
- `PATCH /zoomzoom/order/:param/payment ← zoomzoom-front/src/apis/checkout.ts:138`
- `GET /:paramzendesk/article:param ← zoomzoom-front/src/apis/help.ts:66`
- `GET /:paramzendesk/search ← zoomzoom-front/src/apis/help.ts:78`
- `GET /zoomzoom/order/:param ← zoomzoom-front/src/apis/order.ts:32`
- `GET /:param&files=:param ← zoomzoom-front/src/apis/review.ts:117`
- `GET /v1/search/tour ← zoomzoom-front/src/apis/search.ts:31`
- `POST /v2/social ← zoomzoom-front/src/apis/social.ts:22`
- `DELETE /v2/social ← zoomzoom-front/src/apis/social.ts:40`
- `DELETE /v2/user ← zoomzoom-front/src/apis/user.ts:163`

api 라우트와 짝이 없는 AccessRule (최대 30):

- `route:zoomzoom-back PATCH ^alimtalk$`
- `route:zoomzoom-back GET ^affiliate/me/balance/(\d+)/transaction`
- `route:zoomzoom-back GET ^banner/(\d+)$`
- `route:zoomzoom-back POST ^auth/mobile$`
- `route:zoomzoom-back POST ^auth/mobile/verify$`
- `route:zoomzoom-back POST ^customer/me/social/(\w+)$`
- `route:zoomzoom-back DELETE ^customer/me/social/(\w+)$`
- `route:zoomzoom-back GET ^customer/me/review/(\d+)$`
- `route:zoomzoom-back DELETE ^customer/me/wishlist/(\d+)`
- `route:zoomzoom-back GET ^cms/(\d+)/me$`
- `route:zoomzoom-back PUT ^task/bemyguest/product$`
- `route:zoomzoom-back PATCH ^task/notif/order$`
- `route:zoomzoom-back PATCH ^order/(\d+)/cancel$`
- `route:zoomzoom-back GET ^store/(\d+)/voucher/.*$`
- `route:zoomzoom-back PATCH ^notification/copy$`
- `route:zoomzoom-back DELETE ^group-tag/product$`


## 추출기 report — laravel

### zoomzoom-auth

- 파일 634 · 클래스 594 · 코드 유닛 2136 · DB 접근 지점 402
- 모델 154 (`$table` 있음 127 · 없음 27) · 명령 74 · 스케줄 33 · 라우트 194
- placeholder 로 만든 호출·핸들러 대상: 24건

`$table` 이 없는 모델 (테이블을 추측하지 않음):

- `App\Entities\CustomerData`
- `App\Entities\DndVoucher`
- `App\Entities\HomeServiceMenu`
- `App\Entities\KakaoIdConnectReward`
- `App\Entities\Log`
- `App\Entities\NotificationJob`
- `App\Entities\Permission`
- `App\Entities\Role`
- `App\Entities\ZZTBaseEntiry`
- `App\Entities\ZZTPassportClientBaseEntiry`
- `App\Entities\ZzimcarCoupon`
- `App\Models\Commission`
- `App\Models\Logs\Category`
- `App\Models\Logs\Customer`
- `App\Models\Logs\Customer\Platform`
- `App\Models\Logs\Customer\Referer`
- `App\Models\Logs\Customer\TrackingInfo`
- `App\Models\Logs\Enquiry`
- `App\Models\Logs\EventLog`
- `App\Models\Logs\Order`
- `App\Models\Logs\Product`
- `App\Models\Logs\Review`
- `App\Models\Logs\Review\ReviewContent`
- `App\Models\Logs\Review\ReviewCustomer`
- `App\Models\Logs\Review\ReviewProduct`
- `App\Models\OauthUser`
- `App\Models\User`

`$fillable` 에 있는데 스키마에 없는 컬럼 (상위 20):

- `zoom_address.first_name`
- `zoom_address.last_name`
- `zoom_customer.name`
- `zoom_def_product_schedule_status.text`
- `zoom_notification.data_added`
- `zoom_notification_click.data_added`
- `zoom_product.origin`
- `zoom_product.dest`
- `zoom_product_accommodation.accomodation_type`
- `zoom_product_accommodation.discount_price`
- `zoom_product_accommodation_type.date_updated`
- `zoom_product_description.min_date`
- `zoom_recipient_group.data_added`

Eloquent 호출인데 모델 클래스를 못 찾음 (상위 20):

- `ZzimcarCoupon (no $table)`: 19
- `Request`: 5
- `Token`: 5
- `IP2LocationLaravel`: 5
- `CustomerData (no $table)`: 4
- `DndVoucher (no $table)`: 4
- `NotificationJob (no $table)`: 2
- `Role (no $table)`: 2
- `Permission (no $table)`: 2
- `HomeServiceMenu (no $table)`: 2
- `KakaoIdConnectReward (no $table)`: 2
- `ProductCustomField`: 1
- `MsCommissionRate`: 1

정적/DI 호출 대상 클래스를 못 찾음 (상위 20):

- `Slack`: 22
- `Request`: 16
- `Passport`: 14
- `OAuthServerException`: 9
- `File`: 9
- `Validator`: 7
- `CarbonPeriod`: 6
- `Excel`: 5
- `App`: 4
- `ASDecoder`: 2
- `HTMLDomParser`: 2
- `Cookie`: 2
- `Builder`: 2
- `BelongsToMany`: 2
- `CryptoJsAes`: 1
- `PhoneNumber`: 1
- `Artisan`: 1
- `Client`: 1
- `UnauthorizedException`: 1
- `ResourceServer`: 1


## 추출기 경고

- [schema@1] 17 tables only in urimalo_zzt-2026-04-22.sql (marked missing-from-source): naver_shopping_sales, pricing_management_product, pricing_management_product_price_history, zoom_affiliate_20221216, zoom_affiliate_activity_20221216, zoom_category_backup_20250506, zoom_customer_activity_20221216, zoom_ms_commission_rate_, zoom_ms_requestpayment_20221216, zoom_product_activity_20221216, zoom_product_data_20221216, zoom_product_description_old, zoom_product_to_provider_product_backup, zoom_seller_activity_20221216, zoom_setting_20221216, zoom_temporary_data_20221216, zoom_user_group_20221221
- [schema@1] 2 tables only in local_zzt-2026-10-28.sql (new since hub dump): product_description_management, zoom_seller_charge

## 노드가 없어 버린 관계 (0건, 대상 uid 0개)

문서가 가리키는 컬럼이 스키마에 없거나(문서 부패), 아직 추출기가 없는 코드 유닛(2·3단계)이다.


## 노드가 없어 버린 부분 레코드 (0건)

- 없음
