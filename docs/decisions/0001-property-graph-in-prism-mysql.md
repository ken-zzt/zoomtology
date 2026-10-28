---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-클로드.pdf
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - Service/AgentPrism/src/db-gateway/mcp-endpoint.ts
tags: [decision, storage, prism]
related_to:
  - 0002-git-source-laptop-gets-bundles.md
  - ../design.md
---

# 0001. 속성 그래프로 모델링하고, 저장·조회는 Neo4j 가 아니라 Agent Prism 의 MySQL 과 MCP 도구로 한다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

사전조사 보고서 4건은 모두 **속성 그래프(Property Graph)** 를 권하고(C 1장·O "줌줌투어에는 무엇이 맞는가"·G1 1.2·G2 1장),
저장소로는 **Neo4j Community + 공식 MCP(읽기 전용)** 를 1순위로 꼽았다(C 4.1, G1 4.1, G2 4, O "일순위 구성").
RDF/OWL 은 추론·표준 교환이 필요할 때의 2순위로 뒀다.

그런데 보고서는 "15명 사용자·Ubuntu 서버·DB 5개" 같은 **예시 환경**을 전제했다(O 는 이를 명시적으로 "전제: 예시 값" 이라고 적었다).
줌줌투어의 실제는 다르다.

- 사용자는 셋뿐이다: Ken 의 Claude Code/Codex, mbp2017 의 kenny(Hermes), 개발자 1명. 비개발 팀원의 브라우저 UI 는 1차 범위 밖이다.
- 이미 **Agent Prism** 이 있다 — Ken 이 만든 NestJS MCP 게이트웨이. Google SSO·개인 토큰·스코프·감사 로그·TypeORM·자체 MySQL(`prism-db`)을 갖추고
  Ken 의 Mac(:4100/:4300)과 mbp2017(:4100)에서 돌며, kenny 는 이미 `prism-laptop` MCP 로 붙어 있다.
- 메타데이터만 넣으면 규모가 작다(예상 ~35k 노드·~150k 관계).

## 검토한 선택지

### A. Neo4j Community + 공식 MCP (보고서 권고)
- 장점: Cypher·Browser 시각화, LLM 의 Cypher 생성 품질, 생태계. 보고서들이 검증한 운영 패턴(읽기 전용 MCP + Git PR)
- 단점: 서버 하나가 더 생긴다(docker, 오프라인 덤프 백업, 버전 추적). CE 에는 RBAC 이 없어 네트워크로 막아야 한다. kenny 가 쓰려면 SSH 터널/VPN 경로를 또 만들어야 한다. 사용자 셋에게 Browser UI 는 쓸 일이 거의 없다

### B. Git 원본 + **Agent Prism 자체 MySQL 에 `kg_node/kg_edge`** + Prism MCP 도구 (채택)
- 장점: 새 서버·의존성 0. 인증·스코프(`kg:read`)·감사 로그·배포 경로(`deploy-laptop.sh`)를 그대로 쓴다. kenny 는 클라이언트 설정 변경 없이 같은 `/mcp` 로 새 도구를 본다. MySQL 8 재귀 CTE 로 k-hop·영향도가 이 규모엔 충분하다
- 단점: Cypher 가 없다 — 에이전트는 정해진 도구(`kg_search`·`kg_neighbors`·`kg_impact` 등)만 쓴다. 시각화 UI 가 없다. 그래프 알고리즘(중심성 등)은 직접 짜야 한다

### C. 임베디드 그래프 DB(LadybugDB, 구 Kuzu) + Cypher
- 장점: Cypher 를 쓰면서 서버가 없다
- 단점: Kuzu 는 2025-10 보관(archived)됐고 LadybugDB 는 포크 직후라 안정성·Intel Mac(mbp2017) 바이너리 호환이 불확실하다

### D. Neo4j AuraDB Free (클라우드)
- 장점: 호스팅 없음, 어디서나 접속
- 단점: 테이블·모듈 구조가 외부 SaaS 에 저장된다

## 결정

**B 를 선택한다.** 모델은 보고서대로 속성 그래프(라벨·관계·속성)로 설계하되, 물리 저장과 조회를 Neo4j 대신 Prism 에 얹는다.
그래프의 가치는 "에이전트가 정확한 관계를 근거와 함께 받는 것" 이지 Cypher 자체가 아니다. 1차 역량 질문 20개는 전부 정해진 도구 8개로 답할 수 있다.

## 결과

- Prism 에 `kg` 모듈(마이그레이션·로더·도구·`kg:read` 스코프)이 생긴다. 상세는 AgentPrism ADR 0008(1단계).
- 에이전트가 임의 그래프 질의를 못 쓴다. 새 질문 유형이 생기면 도구를 추가한다. 이게 병목이 되면 그때 Neo4j(A) 또는 Cypher 임베디드(C)를 다시 검토한다 — 번들(JSONL)이 저장소 중립이라 전환 비용이 낮다(ADR 0002).
- 시각화가 필요해지면 번들에서 mermaid/HTML 을 생성하는 쪽을 먼저 본다.
