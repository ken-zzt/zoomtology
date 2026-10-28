# 빌드 report — 20261028T0027Z-ee17d6b

- builtAt: 2026-10-28T00:27:30+00:00  gitSha: ee17d6b
- inputs: {"schema": {"primary": "local_zzt-2026-10-28.sql (502 tables)", "secondary": "urimalo_zzt-2026-04-22.sql (517 tables)", "tables": "519"}, "classification": {"classified": "492", "excluded": "10"}, "docs": {"docs": "102", "statusCodeValues": "124", "domainColumns": "432", "policies": "8", "cronJobs": "59", "glossary": "14", "ownership": "27", "repos": "17"}}

## 건수

| 라벨 | 노드 |
|---|---|
| BusinessRule | 8 |
| Column | 4049 |
| CronJob | 55 |
| Database | 1 |
| Doc | 161 |
| EnumValue | 254 |
| File | 248 |
| Module | 75 |
| Repo | 17 |
| Route | 47 |
| Table | 519 |

| 관계 | 건수 |
|---|---|
| CONTAINS | 519 |
| DOCUMENTED_BY | 580 |
| HAS_COLUMN | 4049 |
| HAS_VALUE | 254 |
| IMPLEMENTS_RULE | 97 |
| REFERENCES | 34 |
| TRIGGERS | 47 |

- 이번 빌드에 처음 보인 노드: 5434
- 지난 빌드엔 있었는데 사라진 uid: 0

- status: {'active': 5249, 'missing-from-source': 185}

## 추출기 경고

- [schema@1] 17 tables only in urimalo_zzt-2026-04-22.sql (marked missing-from-source): naver_shopping_sales, pricing_management_product, pricing_management_product_price_history, zoom_affiliate_20221216, zoom_affiliate_activity_20221216, zoom_category_backup_20250506, zoom_customer_activity_20221216, zoom_ms_commission_rate_, zoom_ms_requestpayment_20221216, zoom_product_activity_20221216, zoom_product_data_20221216, zoom_product_description_old, zoom_product_to_provider_product_backup, zoom_seller_activity_20221216, zoom_setting_20221216, zoom_temporary_data_20221216, zoom_user_group_20221221
- [schema@1] 2 tables only in local_zzt-2026-10-28.sql (new since hub dump): product_description_management, zoom_seller_charge

## 노드가 없어 버린 관계 (0건, 대상 uid 0개)

문서가 가리키는 컬럼이 스키마에 없거나(문서 부패), 아직 추출기가 없는 코드 유닛(2·3단계)이다.


## 노드가 없어 버린 부분 레코드 (0건)

- 없음
