---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-클로드-제미나이2.pdf
  - ontology/schema.yaml
tags: [decision, governance, curation]
related_to:
  - 0003-metadata-only.md
  - 0006-uid-scheme.md
---

# 0005. 자동 추출 위에 큐레이션 오버레이를 얹고(manual > doc > extractor), 모든 노드·관계에 거버넌스 속성을 둔다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

보고서들이 꼽은 실패 요인 1·2위는 "AI 자동 생성 결과를 검수 없이 반영 → 틀린 관계가 쌓여 신뢰 붕괴" 와 "지식 부패(Knowledge Rot)" 다
(C 10장, O "흔한 실패 요인과 예방책", G1 10.1). 처방도 같다: `source`·`verified_by`·`lastVerifiedAt` 같은 속성을 모든 객체에 두고(O "모든 관리 객체의 필수 속성", G2 5.3 필수 속성 6개),
`updatedAt` 과 `lastVerifiedAt` 을 구분하고, 자동 추출은 `confidence: auto`, 사람이 확인하면 `verified` 로 올린다.

줌줌투어 1차 그래프는 대부분 자동 추출이고, 파일럿 도메인만 사람이 확인한다. 둘을 한 그래프에 섞으면서도 "뭐가 확인된 사실인지" 를 잃지 않아야 한다.

## 검토한 선택지

### A. 추출 결과를 그래프 DB 에서 직접 고친다
- 장점: 빠르다
- 단점: 다음 빌드에서 덮어써진다. 누가 왜 고쳤는지 남지 않는다(보고서들이 공통으로 금지한 패턴)

### B. **큐레이션 파일(`curated/*.yaml`)을 오버레이로 병합** — manual > doc > extractor, 밀린 값은 `props.alt.<source>` 에 보존 (채택)
- 장점: 재빌드해도 사람의 판단이 유지된다. Git 이력이 곧 검토 기록. 충돌(추출에 없는 uid, retired 인데 소스에 있음, enum 불일치, FK 모순)을 빌드가 보고한다
- 단점: 큐레이션 파일 문법을 배워야 한다. uid 가 바뀌면 오버레이가 떨어진다(→ ADR 0006 불변 uid)

### C. 추출기 자체에 예외를 하드코딩
- 장점: 파일이 하나 준다
- 단점: 업무 판단이 코드에 묻힌다. 비개발자가 못 고친다

## 결정

**B 를 선택한다.** 거버넌스 속성은 `ontology/schema.yaml` `governance` 가 원본이다.

| 속성 | 값 |
|---|---|
| `source` | 추출기 id(`php@1`), 문서(`doc:<path>`), 사람(`manual`) |
| `confidence` | `auto` / `verified` (`verified` 면 `lastVerifiedAt` 필수) |
| `status` | `active` / `missing-from-source` / `retired` |
| `firstSeenAt` / `lastSeenAt` | 빌드 기준(`state/first-seen.tsv`) |
| `lastVerifiedAt`, `verifiedBy` | 사람이 "지금도 사실" 이라고 확인한 날·사람 |
| `sourceRef` | 근거 위치 `repo/path:line[-line]`, 문서 경로, curated 파일 경로 |

큐레이션 의미: `add`(추출에 없는 노드·관계, 예: 논리 FK) · `override`(meaning/summary/status/domain) · `supersede`(`SUPERSEDES` + retired).
드리프트: 지난 빌드엔 있었는데 사라진 uid — `verified` 는 tombstone(`missing-from-source`)으로 남기고, `auto` 는 지우고 report 에 적는다.

## 결과

- 에이전트 답변은 "그래프 경로 + `sourceRef`" 를 근거로 낼 수 있다(O "좋은 답" 예시). `confidence: auto` 인 관계는 그렇게 표시해서 말한다.
- 사람이 확인할 큐(`lastVerifiedAt` 90일 초과, steward 없음)는 Prism 도구가 아니라 빌드 report 가 낸다(1차).
- 큐레이션 파일 문법은 `curated/README.md` 에 둔다(4단계에 확정).
