# 다음 슬라이스 — 부서·역할·업무 프로세스 (메모, 2026-10-28)

1차(ZDV-343)는 DB ↔ 코드 ↔ 진입점만 담았다. 다음 슬라이스는 **누가(부서·역할) 무엇을(프로세스) 어떤 화면·크론·큐로 하는가**를 얹는다. 여기 적는 것은 결정이 아니라 1차를 끝내며 보이는 길이다. 시작할 때 ADR 로 확정한다.

## 자리 (이미 예약)

- `schema.yaml` `reserved_prefixes`: `dept:` `role:` `process:` `person:` — 추출기는 만들 수 없다(빌드가 막는다). 다음 슬라이스에서 라벨 `Department`·`Role`·`Process`(·`Person` 은 보류)를 추가하고 예약을 푼다.
- 관계 후보: `Department -OWNS-> Domain|Table|Route`, `Role -PERFORMS-> Process`, `Process -HAS_STEP-> Process`, `Process -USES-> Route|CronJob|QueueMessage|Table`, `Person -HOLDS-> Role`.
- 파일럿 프로세스 `curated/processes/order-to-settlement.yaml` 은 지금 Doc 노드(`doc:zoomtology/curated/processes/…`) + 단계별 `DOCUMENTED_BY{section: <step id>}` 다. v1.1 에서 `curated.py apply_process` 를 한 군데만 바꿔 `process:<slug>` 노드 + `HAS_STEP`(단계 = `process:<slug>/<step id>`) + `USES`(refs) 로 내보낸다. 파일 문법은 그대로 둔다 — Ken 이 쓰는 YAML 은 바뀌지 않는다.

## 출처 (어디서 뽑나)

| 대상 | 원본 | 방법 |
|---|---|---|
| 부서·역할 | `zoomzoom-playbook`(팀 업무 SOP — 조직·운영·CS·세일즈·마케팅) | 문서 추출기(docs.py 와 같은 꼴): 프론트매터·표에서 부서·역할·담당 화면을 읽는다. playbook 은 비개발 팀원이 쓰는 저장소라 **읽기만** 한다 |
| 프로세스 | playbook 의 SOP 절, `zoomzoom-services/docs/00-overview/request-flows.md`, 어드민 매뉴얼(`70-manuals/`) | 단계 = 화면(Route)·크론·큐 메시지. 1차 그래프의 Route/CronJob/QueueMessage uid 를 그대로 가리킨다 |
| 화면 → 부서 | 어드민 권한 그룹(`zoom_user_group`·`admin/controller/user/permission`) | 권한 그룹 = 역할의 근사. 라우트별 `access` 목록을 읽어 `Role -PERFORMS-> Route` 초안 |
| 사람 | 쓰지 않는다 | 개인정보·조직 변동. `Person` 은 필요해질 때 Prism 권한 모델과 같이 결정 |

## 역량 질문 후보

1. "환불 승인은 어느 부서가 어떤 화면에서 하나?" → `process:refund` → HAS_STEP → USES Route → `Department -OWNS-> Route`.
2. "정산 프로세스에서 크론이 하는 단계와 사람이 하는 단계는?" → Process 단계의 actor(크론/역할).
3. "CS 팀이 쓰는 어드민 화면이 읽는 테이블은?" → Role → Route → HANDLES → CodeUnit → READS.
4. "이 테이블을 바꾸면 어느 부서 업무가 멈추나?" → `kg_impact` 를 Process·Department 까지 거슬러 올라가게 `impact_flow` 에 USES·OWNS 를 추가.

## 비용·순서 제안

1. Process 노드 전환(로더 한 군데) + 파일럿 프로세스 1개 → `kg_impact` 가 프로세스까지 답하는지 본다. 반나절.
2. playbook 에서 부서·역할 표 추출(문서 꼴 확인 뒤) → `curated/departments.yaml` 초안. 1~2일.
3. 어드민 권한 그룹 → 역할·화면 매핑 초안. 1일.
4. 역량 질문 4개로 검증, kenny AGENTS 에 한 줄.

## 1차에서 남긴 것 (다음 슬라이스 전에 정리해도 되는 것)

- PHP 헬퍼 조립 SQL(테이블 자리를 못 찾은 쿼리 admin 204·partners 417) — tree-sitter 업그레이드 판단은 report 의 그 숫자가 줄지 않으면.
- `zoomzoom-front` 페이지(Route front)는 안 만들었다. 화면 단위 질문이 생기면 Next.js 라우트(`src/app/**`)를 Route(front)로.
- `document-api`·`zoomzoom-chat` 은 추출하지 않았다(각각 placeholder Route 로만 보인다).
