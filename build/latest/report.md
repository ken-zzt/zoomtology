# 빌드 report — 20261028T0555Z-e352549-dirty

- builtAt: 2026-10-28T05:55:45+00:00  gitSha: e352549 (dirty)
- inputs: {"schema": {"primary": "local_zzt-2026-10-28.sql (502 tables)", "secondary": "urimalo_zzt-2026-04-22.sql (517 tables)", "tables": "519"}, "classification": {"classified": "492", "excluded": "10"}, "docs": {"docs": "102", "statusCodeValues": "124", "domainColumns": "432", "policies": "8", "cronJobs": "59", "glossary": "14", "ownership": "27", "repos": "17"}, "php": {"zoomzoom-admin": "files=879 classes=906 units=8417 queries=5559", "zoomzoom-partners": "files=463 classes=487 units=4461 queries=2875", "placeholders": "46"}}

## 건수

| 라벨 | 노드 |
|---|---|
| BusinessRule | 8 |
| CodeUnit | 12924 |
| Column | 4049 |
| CronJob | 55 |
| Database | 3 |
| Doc | 161 |
| EnumValue | 272 |
| File | 1560 |
| Module | 60 |
| Queue | 2 |
| QueueMessage | 5 |
| Repo | 17 |
| Route | 2758 |
| Table | 527 |

| 관계 | 건수 |
|---|---|
| CALLS | 14503 |
| CONTAINS | 14803 |
| DEFINES | 81 |
| DOCUMENTED_BY | 580 |
| HANDLES | 2855 |
| HAS_COLUMN | 4049 |
| HAS_VALUE | 272 |
| IMPLEMENTS_RULE | 97 |
| JOINS | 1172 |
| PUBLISHES | 10 |
| READS | 6863 |
| REFERENCES | 432 |
| TRIGGERS | 47 |
| WRITES | 2762 |

- 이번 빌드에 처음 보인 노드: 22401
- 지난 빌드엔 있었는데 사라진 uid: 34

### 사라진 uid (verified 는 tombstone 대상 — 4단계에서 처리)

- `module:data-api/Dockerfile`
- `module:data-api/Makefile`
- `module:design-system/vite.config.mts`
- `module:devenv/auth/sites/default.conf`
- `module:devenv/env/copy-deny.txt`
- `module:devenv/env/repos.list`
- `module:devenv/logrotate/zzt.conf`
- `module:devenv/nginx/snippets/partner.conf`
- `module:devenv/nginx/snippets/user.conf`
- `module:devenv/templates/auth/sites/default.conf.tmpl`
- `module:devenv/templates/nginx/sites-available/default.tmpl`
- `module:devenv/templates/nginx/sites-available/user.tmpl`
- `module:devenv/templates/nginx/zzt/user.env.conf.tmpl`
- `module:message-consumer/Makefile`
- `module:partner-app/Makefile`
- `module:user-app/Makefile`
- `module:zoomzoom-api/Makefile`
- `module:zoomzoom-front/Makefile`
- `module:zoomzoom-partners/deploy/Dockerfile`
- `module:zoomzoom-partners/deploy/nginx/partners.conf`
- `module:zoomzoom-partners/deploy/nginx/zzt-http.conf`
- `module:zoomzoom-partners/deploy/php/99-zzt-partners.ini`
- `module:zoomzoom-partners/deploy/php/fpm-pool.conf`
- `route:zoomzoom-admin route=cron/tasks/checkContinuouslyBlockedDays`
- `route:zoomzoom-admin route=cron/tasks/confirmBatchPayoutBalance`
- `route:zoomzoom-admin route=cron/tasks/emailTaskRun`
- `route:zoomzoom-admin route=cron/tasks/payoutEstimate`
- `route:zoomzoom-admin route=cron/tasks/payoutMarkDone`
- `route:zoomzoom-admin route=cron/tasks/resetCampaignCredits`
- `route:zoomzoom-admin route=cron/tasks/updateElasticSearchData`
- `route:zoomzoom-admin route=cron/tasks/updateTransactionFee`
- `route:zoomzoom-admin route=task/task/checkProviderOrderStatus`
- `route:zoomzoom-admin route=task/task/rejectOrderAfterWeek`
- `route:zoomzoom-admin route=task/task/runUpdateStats`

- status: {'active': 22170, 'missing-from-source': 231}

## 추출기 report — php

### zoomzoom-admin

- 파일 879 · 클래스 906 · 코드 유닛 8417 · `->query(` 5559건
- 테이블 자리를 못 찾은 쿼리: 204건 (헬퍼가 조립하는 SQL·SHOW/DESCRIBE — tree-sitter 업그레이드 판단 자료)
- 테이블 이름은 있는데 전부 스키마에 없는 쿼리: 289건 (폐기 테이블·결제 확장)
- 테이블 자리가 변수인 쿼리: 36건
- 클래스는 있는데 메서드가 없어 placeholder 를 가리킨 호출: 214건
- 큐 발행 role 별 건수: {'order': 3, 'push': 1} · key 를 못 읽은 sendMessage: 1건

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
- 큐 발행 role 별 건수: {'order': 5, 'push': 1}

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


## 추출기 경고

- [schema@1] 17 tables only in urimalo_zzt-2026-04-22.sql (marked missing-from-source): naver_shopping_sales, pricing_management_product, pricing_management_product_price_history, zoom_affiliate_20221216, zoom_affiliate_activity_20221216, zoom_category_backup_20250506, zoom_customer_activity_20221216, zoom_ms_commission_rate_, zoom_ms_requestpayment_20221216, zoom_product_activity_20221216, zoom_product_data_20221216, zoom_product_description_old, zoom_product_to_provider_product_backup, zoom_seller_activity_20221216, zoom_setting_20221216, zoom_temporary_data_20221216, zoom_user_group_20221221
- [schema@1] 2 tables only in local_zzt-2026-10-28.sql (new since hub dump): product_description_management, zoom_seller_charge

## 노드가 없어 버린 관계 (0건, 대상 uid 0개)

문서가 가리키는 컬럼이 스키마에 없거나(문서 부패), 아직 추출기가 없는 코드 유닛(2·3단계)이다.


## 노드가 없어 버린 부분 레코드 (0건)

- 없음
