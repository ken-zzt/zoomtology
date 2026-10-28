---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - Service/zoomzoom-services/reference/schema/urimalo_zzt-2026-04-22.sql
  - Service/zoomzoom-services/tools/scan-table-usage.sh
tags: [decision, extraction, schema]
related_to:
  - 0007-first-slice-scope-and-pilot.md
---

# 0004. 테이블 관계는 FK 가 아니라 코드(조인·로직)에서 뽑는다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

보고서들은 DB 스키마를 `information_schema` 에서 자동 수집해 테이블·컬럼·**FK** 로 그래프의 뼈대를 만들라고 했고(C 7장 4단계, G1 4.1 OpenMetadata, G2 tbls),
G1·G2 는 OpenMetadata/tbls 같은 카탈로그 도구로 "600개 테이블을 자동 수집" 하는 것을 1순위로 봤다.

줌줌투어 DB 를 세어 보니(2026-10-28, 로컬 `local_zzt`): 테이블 502·컬럼 3,883 에 **FK 는 34개**. 컬럼 코멘트 975, 테이블 코멘트 15.
즉 FK 로 그리면 관계가 거의 없는 그래프가 나온다. 실제 관계는 레거시 PHP 의 문자열 SQL(JOIN)과 NestJS 의 QueryBuilder/리포지토리 호출 안에 있다.
O 보고서도 "ERD 만 신뢰 → 업무상 논리 관계와 실제 사용이 빠짐. 인터뷰·코드·DB 를 교차검증" 을 실패 요인 표에 적었다.

## 검토한 선택지

### A. 카탈로그 도구(OpenMetadata/DataHub/tbls)로 스키마 자동 수집
- 장점: 설치하면 테이블·컬럼·FK·코멘트가 나온다
- 단점: FK 34개로는 관계가 안 나온다. OpenMetadata 는 운영 권장 사양이 크고(서버·DB·검색엔진 각 4~16GiB), MCP 모듈 라이선스가 별도(Collate)다. 이 환경엔 과하다

### B. **코드에서 관계를 뽑는다** — PHP 정규식+`$sql` 데이터플로, NestJS ts-morph, 스키마는 덤프 파싱 (채택)
- 장점: 실제로 어느 코드가 어느 테이블을 읽고 쓰고 조인하는지가 나온다 — 이게 1차 그래프의 존재 이유다. FK 가 없는 논리 참조(`zoom_order.product_id → zoom_product`)는 조인 ON 절과 큐레이션으로 채운다
- 단점: 추출기를 직접 만든다. 정규식의 정밀도 상한(헬퍼로 조립되는 SQL 누락). 저장소마다 방식이 다르다(PHP 2종·Laravel·NestJS)

## 결정

**B 를 선택한다.** 스키마(테이블·컬럼·FK 34·코멘트)는 `mysqldump --no-data` 와 허브 덤프를 파싱해 노드로 만들고,
**관계는 코드 추출(READS/WRITES/JOINS/REFERENCES-logical)과 큐레이션(REFERENCES-verified)** 으로 만든다.
`zoomzoom-services/tools/scan-table-usage.sh` 가 이미 같은 방향의 단순판(파일 수)이라 교차검증 기준으로 쓴다.

## 결과

- 추출 정밀도를 수치로 관리한다: 2단계에서 `->query(` 40곳 무작위 수검(목표 ≥90%), report 에 "query 는 있는데 테이블 0" 메서드 목록.
- 정규식이 부족하면 `py-tree-sitter` + tree-sitter-php 로 올린다(PHP 런타임 불필요). 그 판단은 report 숫자로 한다.
- 카탈로그 도구는 "DB 엔진·수가 늘고 컬럼 수준 리니지·RBAC 가 필요해질 때"(O "육 개월 시점 기술 확장 기준") 다시 본다.
