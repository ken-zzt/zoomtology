---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-클로드.pdf
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - docs/competency-questions.md
tags: [decision, scope, pilot]
related_to:
  - 0001-property-graph-in-prism-mysql.md
  - 0004-relationships-from-code-not-fk.md
---

# 0007. 1차 범위는 DB↔코드↔진입점이고, 파일럿은 주문→결제→취소/환불→정산 이다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

보고서들의 1차 범위는 **부서·업무 프로세스·단계 ↔ 시스템 ↔ 테이블** 이었다(C 5장 클래스 15개, G1·G2 BBO 기반 Process/Task, O 의 Department/Role/ProcessStep).
파일럿 후보도 그 관점에서 "예약→결제→확정→정산"(C), "결제·바우처 발급"(G1), "예약-확정-발권"(G2), "예약 취소→환불→정산"(O) 이었다.
공통 조언은 하나다: "처음부터 전사를 모델링하지 말고 프로세스 하나를 끝까지, 역량 질문 20개로 완료 판정" (C 10장, O, G1 10.1, G2 10).

Ken 의 첫 과제는 그보다 앞에 있다 — **DB 와 소스코드 로직의 관계**를 에이전트(Claude Code·Codex·kenny)가 참조하게 하는 것.
부서·역할·비즈니스 모델은 "그 후에 자연스럽게" 얹는다. 지금 그래프의 사용자는 사람이 아니라 에이전트 셋이다.

## 검토한 선택지

### A. 보고서대로 부서·프로세스 매핑부터
- 장점: 비개발 팀원에게 가치가 바로 보인다
- 단점: 부서 인터뷰·워크숍이 필요하다(회사 10명 미만, Ken 의 시간이 병목). 에이전트의 당장 필요(어느 코드가 어느 테이블을 쓰나)를 못 푼다. 코드↔테이블 층이 없으면 프로세스 단계의 READS/WRITES 를 손으로 적어야 한다

### B. **DB↔코드↔진입점(라우트·큐·크론)을 먼저, 자동 추출 중심** (채택)
- 장점: 대부분 자동으로 나온다(ADR 0004). 에이전트가 즉시 쓴다. 나중에 Process 노드가 붙을 때 "단계 → 시스템 → 코드 → 테이블" 을 이어 줄 바닥이 된다
- 단점: 비개발 팀원에겐 당장 보이는 게 없다. 업무 의미는 문서 허브의 정책·용어집을 빌려 오는 정도

### C. 둘 다 한 번에
- 단점: 보고서 전부가 경고한 "처음부터 전사" 실패 패턴

## 결정

**B 를 선택한다.** 범위:
- 넣는다: Repo·Service·Module·File·CodeUnit·Route·Queue·QueueMessage·CronJob·Database·Table·Column·EnumValue·BusinessRule(정책 문서)·Domain·ExternalService·Doc, 관계 20종.
- 예약만: `dept:` `role:` `process:` `person:` 접두사. 파일럿 프로세스(`curated/processes/order-to-settlement.yaml`)는 1차에서 Doc 노드로 내보내고 v1.1 에 Process 로 전환한다.
- 안 넣는다: 비개발 팀원 UI, 벡터 검색/GraphRAG(O: "1차에서는 vector embedding 이 반드시 필요하지 않다"), 자동 CI 빌드.

**파일럿은 주문→결제→취소/환불→정산** 이다. 시스템·테이블 교차가 가장 많고(PHP admin·partners, zoomzoom-api, order 큐, admin 크론, 정책 문서 9건 중 6건), Ken 이 ZDV-106/122 로 최근 깊이 본 영역이라 검증 비용이 낮다.
완료 판정은 [`docs/competency-questions.md`](../competency-questions.md) 20개가 Prism 도구로 답해지는지(`tests/cq/`).

## 결과

- 6주 5단계(ZDV-344~349). Ken 검토 주 2~3시간, 실작업은 에이전트.
- 파일럿 밖 영역은 `confidence: auto` 로만 존재한다. 답변 시 그 사실을 함께 말한다.
- 다음 슬라이스(부서·역할·프로세스)는 5단계 끝에 결정 메모로 남긴다.
