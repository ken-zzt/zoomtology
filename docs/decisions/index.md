---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources: []
tags: [index, zoomtology]
related_to: []
---

# zoomtology 설계 결정 기록 (ADR)

"왜 이렇게 설계했나"를 남긴다. **대안 비교가 있는 결정만** 기록한다. 설계 내용 자체는 [design.md](../design.md) 가 원본이고, 여기는 선택의 근거만 담는다.
형식은 `zoomzoom-services/templates/adr.md` (AgentPrism 과 같다). 파일명 `NNNN-슬러그.md`.

사전조사 보고서 4건은 [research/](../research/) 에 있다. 각 ADR 은 어느 보고서의 어느 절이 근거였는지 적는다.
보고서 약칭: **C** = 클로드, **G1** = 클로드-제미나이, **G2** = 클로드-제미나이2, **O** = 챗지피티.

| 번호 | 결정 | 상태 |
|---|---|---|
| [0001](0001-property-graph-in-prism-mysql.md) | 속성 그래프로 모델링하고, 저장·조회는 Neo4j 가 아니라 Agent Prism 의 MySQL 과 MCP 도구로 한다 | 채택 |
| [0002](0002-git-source-laptop-gets-bundles.md) | Git 저장소(zoomtology)가 원본이고 그래프 DB 는 재생성 가능한 산출물이다. 노트북(mbp2017)엔 번들만 보낸다 | 채택 |
| [0003](0003-metadata-only.md) | 그래프에는 메타데이터(이름·위치·관계·의미)만 넣는다. 코드 본문·SQL 원문·비밀 값·실데이터는 넣지 않는다 | 채택 |
| [0004](0004-relationships-from-code-not-fk.md) | 테이블 관계는 FK 가 아니라 코드(조인·로직)에서 뽑는다 | 채택 |
| [0005](0005-curated-overlay-and-governance.md) | 자동 추출 위에 큐레이션 오버레이를 얹고(manual > doc > extractor), 모든 노드·관계에 거버넌스 속성을 둔다 | 채택 |
| [0006](0006-uid-scheme.md) | uid 는 불변 소문자 ASCII 식별자이고 사람이 보는 이름과 분리한다 | 채택 |
| [0007](0007-first-slice-scope-and-pilot.md) | 1차 범위는 DB↔코드↔진입점이고, 파일럿은 주문→결제→취소/환불→정산 이다 | 채택 |

AgentPrism 쪽 결정(kg 모듈이 `/mcp` 를 공유하고 `kg:read` 스코프를 쓴다)은 `AgentPrism/docs/decisions/0008-kg-in-prism-mysql.md` 에 둔다(1단계, ZDV-345).

폐기된 결정도 지우지 않는다. `status: archived` 로 내리고 대체 ADR 번호를 적는다.
