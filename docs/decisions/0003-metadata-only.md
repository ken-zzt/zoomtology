---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-클로드.pdf
  - Service/kenny-agents/docs/90-decisions/0020-code-confidentiality-rules.md
  - ontology/schema.yaml
tags: [decision, security, kenny]
related_to:
  - 0002-git-source-laptop-gets-bundles.md
---

# 0003. 그래프에는 메타데이터(이름·위치·관계·의미)만 넣는다. 코드 본문·SQL 원문·비밀 값·실데이터는 넣지 않는다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

보고서들의 보안 1원칙은 "실데이터(고객·예약·결제 행) 금지, 메타데이터만" 이다(C 9장 ①, O "가장 중요한 모델링 원칙", G1 8.1, G2 8).
줌줌투어엔 한 겹이 더 있다. kenny 의 code-guard(ADR 0020)는 **저장소 소스 텍스트가 Slack 으로 나가는 것을 막는다.**
허용되는 것은 위치 정보(저장소·파일 경로·함수·테이블·컬럼 이름)다(R2). 코드 저장소 안의 SQL·설정도 코드다(R5).
그래프 내용은 kenny 의 답변 근거가 되므로, 그래프에 코드 조각이 들어가면 그대로 Slack 으로 샐 수 있다.

Ken 은 2026-10-28 에 "그래프 메타데이터는 코드가 아니므로 kenny 가 Slack 답변에 써도 된다" 고 정했고, 회색지대 셋도 허용했다.

## 검토한 선택지

### A. 메타데이터만 — 이름·위치·관계·의미 (채택)
- 장점: code-guard 와 충돌하지 않는다. 그래프가 작다. 외부 LLM 으로 나가는 정보가 구조 정보로 한정된다
- 단점: "이 함수가 정확히 무슨 SQL 을 날리나" 는 그래프로 못 보고 코드를 열어야 한다(그래서 `sourceRef` 에 줄 범위를 둔다)

### B. SQL 문장·코드 조각도 저장
- 장점: 에이전트가 코드를 안 열어도 된다
- 단점: kenny 경로에서 소스가 샌다. 번들이 커진다. 시크릿이 섞일 위험이 는다

## 결정

**A 를 선택한다.** 허용/불허는 다음과 같다.

허용(그래프에 넣고 kenny 에게도 보임):
- 테이블·컬럼 이름·타입, 저장소·파일 경로·클래스·함수명 (ADR 0020 R2 와 같다)
- 코드 유닛의 **줄 범위**(`sourceRef`: `order_info.php:120-145`)
- 코드에서 뽑은 **구조 관계**(호출·읽기/쓰기 테이블·조인·발행/소비·라우트 처리)
- 컬럼 설명·enum 의미(문서 허브·DDL 코멘트 출처) 및 **코드 안에만 정의된 enum 리터럴**(예: `1 = book_requested`)

불허(어떤 산출물에도 넣지 않는다):
- SQL 원문, 코드 본문(`CodeUnit` 에 `body`·`source`·`sql` prop 금지)
- DDL 기본값(`Column.default` 금지 — 토큰·키가 들어갈 수 있다)
- `zoomzoom-admin/scripts/` 의 자격증명, `.env`, `config.php` 등 거부 경로의 내용
- 고객·예약·결제 **행** 데이터

강제 수단은 두 겹이다: 빌드(`extractors/zoomtology/schema.py` + `guard.py`, `schema.yaml` 의 `content_guard`)와 Prism 로더(`content-guard.ts`). 어느 쪽이든 걸리면 실패한다.

## 결과

- 추출기는 문자열 리터럴을 테이블·컬럼·enum·라우트·큐 키 토큰으로만 남기고 SQL 텍스트는 즉시 버린다.
- Prism 스코프는 `kg:read` 하나다. 함수 수준을 kenny 에게 숨길 필요가 생기면 `kg:read-detail` 로 분리한다.
- 보고서가 권한 "민감 시스템은 별도 confidential 라벨" (C 9장 ⑤)은 1차엔 쓰지 않는다. 필요해지면 `sensitivity` prop 과 스코프로 푼다.
