---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - ontology/uid.md
  - ontology/schema.yaml
tags: [decision, identity]
related_to:
  - 0005-curated-overlay-and-governance.md
---

# 0006. uid 는 불변 소문자 ASCII 식별자이고 사람이 보는 이름과 분리한다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

O 보고서 "이름 규칙": "사람이 바꾸는 이름과 ID 를 분리해야 한다. … 나중에 '예약 시스템' 이 'Core Booking' 으로 이름을 바꿔도 uid 는 그대로다."
실패 요인 표에도 "ID 에 display name 사용 → 명칭 변경 시 graph 가 깨짐 → immutable uid" 가 있다.
줌줌투어에선 저장소 이름이 이미 한 번 바뀌었고(zoomzoomtour→zoomzoom-admin, zzt-api→zoomzoom-auth, 2026-10-20),
파트너 저장소의 `zoomtu` 가 admin 과 포크로 갈라져 같은 클래스명이 두 저장소에 있다.
큐레이션 오버레이(ADR 0005)와 Prism 도구·테스트는 전부 uid 로 노드를 찾으므로 규칙이 먼저 고정돼야 한다.

## 검토한 선택지

### A. UUID
- 장점: 충돌 없음
- 단점: 사람이 못 읽는다. 추출기를 다시 돌리면 같은 대상에 다른 UUID 가 나와 상태 추적이 안 된다

### B. **결정적(deterministic) 경로형 uid** `<prefix>:<path>` (채택)
- 장점: 같은 대상은 몇 번을 추출해도 같은 uid. 사람이 읽고 손으로 쓸 수 있다(큐레이션 YAML). 접두사로 라벨이 보인다
- 단점: 파일 이동·클래스 이름 변경 시 uid 가 바뀐다 → `SUPERSEDES` 로 잇고 옛 uid 는 retired 로 남긴다

### C. 사람이 보는 이름을 그대로 키로
- 단점: 보고서가 지적한 그 문제

## 결정

**B 를 선택한다.** 규칙은 [`ontology/uid.md`](../../ontology/uid.md), 정규식은 `schema.yaml` `labels.<Label>.uid`.

- 라벨마다 접두사 하나(`repo:` `svc:` `module:` `file:` `code:` `route:` `queue:` `msg:` `cron:` `db:` `table:` `col:` `enum:` `rule:` `domain:` `ext:` `doc:`), 예약 `dept:` `role:` `process:` `person:`.
- 코드 심볼·HTTP 메서드는 코드에 있는 그대로(대소문자 유지). 그 외는 소문자. 한글은 uid 에 넣지 않는다.
- 저장소 이름은 `repos.tsv` 의 `name`. 두 저장소의 같은 클래스는 저장소 접두사로 구분된다(`code:zoomzoom-admin/...#ZZTCoupon` vs `code:zoomzoom-partners/...#ZZTCoupon`).
- 테이블 접두사 `zoom_` 은 떼지 않는다(접두사 없는 테이블과 충돌).
- 폐기된 uid 는 재사용하지 않는다.

## 결과

- 추출기는 `extractors/zoomtology/model.py` 의 uid 생성기만 쓴다. 손으로 문자열을 조립하지 않는다.
- 저장소가 또 이름을 바꾸면 모든 uid 가 바뀐다 — 그때는 빌드가 `SUPERSEDES` 를 일괄 생성하는 마이그레이션 스크립트를 쓴다(필요해질 때 만든다).
