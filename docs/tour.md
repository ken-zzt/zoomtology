# zoomtology 한 시간 투어 — 우리가 뭘 만들었나

읽는 사람: Ken. 목적: 코드를 읽지 않고도 이 물건의 **구조·내용·쓰는 법·고치는 법**을 머리에 넣는다. 30분 읽고, 30분은 직접 질문해 본다(6절).

## 1. 한 문장

**줌줌투어의 DB 테이블·코드·실행 진입점(화면 라우트·크론·큐)이 서로 어떻게 이어지는지를 "이름과 관계"로만 뽑아 둔 표**다. 코드 본문은 없다. 에이전트(Claude Code, kenny)가 코드를 뒤지기 전에 이 표에 먼저 묻는다.

비유하면 **건물 배선도**다. 벽을 뜯지 않아도 "이 스위치를 끄면 어느 방 불이 꺼지나"를 알 수 있다. 벽 속 전선(코드 본문)은 배선도에 없고, 필요하면 그때 뜯는다.

## 2. 그림 — 어디서 와서 어디로 가나

```
 입력 (읽기만 한다)                    추출기 (Python + node)              산출물                    서비스                  사용자
 ───────────────────                  ─────────────────────              ────────                  ──────                  ──────
 local_zzt 스키마 덤프  ──schema──┐
 AgentPrism tables.yaml ─classification─┤
 zoomzoom-services 문서 ──docs────┤
 zoomzoom-admin·partners(PHP) ─php─┼──▶ 병합·검증 ──▶ 번들 tar.gz ──▶ Prism MySQL ──▶ MCP 도구 kg_* ──▶ Claude Code / Codex
 zoomzoom-api·consumer·back·   ─ts──┤   (Collector)      (nodes.jsonl        (kg_node,              (8개)                  kenny (Slack)
   external-api·data-api·front       │                    edges.jsonl         kg_edge)
 zoomzoom-auth(Laravel) ──laravel──┤                    manifest.json
 curated/*.yaml (사람 손) ─curated──┘                    report.md)
```

- **왼쪽**은 전부 지금 있는 것들이다. 아무것도 고치지 않고 읽기만 한다.
- **추출기**는 이 저장소 `extractors/` 에 있다. 하나씩 돌아 "노드"와 "관계"를 내놓고, `Collector` 가 같은 것끼리 합친다.
- **번들**은 결과 파일 묶음이다. 텍스트 두 파일(노드·관계)이 핵심이고, 빌드할 때마다 `bundle/<버전>` 태그로 남는다.
- **Prism** 은 Ken 이 만든 Agent Prism 이다. 번들을 자기 MySQL 두 테이블에 넣고, 같은 `/mcp` 주소로 도구 8개를 낸다. Prism 이 셋 있다 — 메인 Mac dev(:4300), 메인 Mac pm2(:4100, `prism-local-opdb`), 노트북 mbp2017(:4100, kenny 용). 번들은 세 곳에 따로 넣는다.
- **사용자**는 사람이 아니라 에이전트다. 사람은 에이전트에게 묻는다.

## 3. 무엇을 담았나 — 노드와 관계

그래프는 **노드**(점)와 **관계**(선)로 돼 있다. 노드 17종, 관계 20종. 전부 외울 필요 없고, 아래 묶음으로 보면 된다.

| 묶음 | 노드 | 예 | 어디서 왔나 |
|---|---|---|---|
| DB | Database · Table · Column · EnumValue | `table:zoom_order`, `col:zoom_order.order_status_id`, `enum:zoom_order.order_status_id=2` | 스키마 덤프, status-codes.md, 코드의 상수 배열 |
| 코드 | Repo · Service · Module · File · CodeUnit | `code:zoomzoom-admin/system/library/zoomtu/order_info.php#ZZTOrderInfo::updateStatus` | PHP·TS·Laravel 추출기 |
| 진입점 | Route · CronJob · Queue · QueueMessage | `route:zoomzoom-api PATCH /order/:id/confirm`, `cron:admin/cron/tasks/statuscheck`, `msg:order/confirm-order` | 컨트롤러, scheduled-jobs.md, SQS 코드 |
| 의미 | Domain · BusinessRule · Doc · ExternalService | `domain:settlement`, `rule:partial-refund`, `doc:…/policies/partial-refund.md` | curated, 정책 문서 |

관계도 묶음으로.

| 뜻 | 관계 | 읽는 법 |
|---|---|---|
| 담고 있다 | CONTAINS, HAS_COLUMN, HAS_VALUE | 파일이 메서드를, 테이블이 컬럼을, 컬럼이 enum 값을 |
| 코드가 DB 를 건드린다 | READS, WRITES, MAPS_TO, JOINS, REFERENCES | 메서드가 테이블을 읽는다/쓴다, 엔티티가 테이블에 대응, 두 테이블이 같이 조인된다, 컬럼이 다른 컬럼을 가리킨다(논리 FK) |
| 코드가 코드를 부른다 | CALLS, CALLS_HTTP | 메서드가 메서드를, 서비스가 다른 서비스의 라우트를 |
| 진입점이 코드를 돈다 | HANDLES, TRIGGERS, PUBLISHES, CONSUMES | 라우트의 핸들러, 크론이 때리는 라우트, 큐 메시지를 내고 받는 코드 |
| 의미를 붙인다 | BELONGS_TO_DOMAIN, IMPLEMENTS_RULE, DOCUMENTED_BY, SUPERSEDES | 정산 도메인에 속한다, 이 정책을 구현한다, 이 문서가 근거다, 새 코드가 옛 코드를 대체한다 |

**이름(uid)** 은 `종류:경로` 꼴이고 절대 바뀌지 않는다. 규칙은 [`ontology/uid.md`](../ontology/uid.md). 사람이 읽는 이름(`name`)은 따로 있다.

### zoom_order 하나를 따라가 보면 (2026-10-28 번들 실제 값)

- `table:zoom_order` — 컬럼 85개(`HAS_COLUMN` 85). 이 테이블을 **읽는 메서드 350개, 쓰는 메서드 93개**. 함께 조인되는 테이블 67개 — 가장 많이 조인되는 건 `zoom_ms_requestpayment`(97번, `order_id` 로). 정산 문서 2건이 근거로 붙어 있다. 도메인은 `domain:order`.
- 쓰는 쪽 예 — zoomzoom-api 의 `UpdateOrderRepository::completePayment` 가 `update`·`upsert` 를 한다. 근거 `zoomzoom-api/src/order/infra/persistence/orm/repositories/update-order.repository.ts:355`. 레거시 쪽은 `ZZTOrderInfo::updateStatus`(`order_info.php:34-39`).
- `col:zoom_order.order_status_id` — enum 값 0 신규(결제 전), 1 예약요청, 2 예약확정, 3 예약거절, 4 결제실패(미사용), 5 환불, 6 예약대기, 81 결제시작. 한글 뜻은 Ken 이 승인한 curated 에서, 영문 라벨은 코드의 `ZZTOrderInfo::$order_status_string` 에서 왔다.
- `zoom_order` 를 바꾸면 영향받는 크론 — `payoutestimate`, `confirmbatchpayoutbalance`, `checkproviderorderstatus`, Laravel `confim-mileage`(4단계 깊이). 라우트 370개. 이게 `kg_impact` 가 내는 답이다.
- 알게 된 것 하나 — `zoom_order` 테이블의 DB 코멘트가 "예약금 비율…"이다. `deposit_rate` 컬럼 설명이 테이블 코멘트에 잘못 들어가 있다. 그래프는 DB 를 그대로 비추니 이런 게 보인다.

## 4. 모든 점과 선에 붙은 꼬리표 (거버넌스)

노드·관계마다 네 가지가 붙는다. 답을 믿을지 판단하는 근거다.

| 꼬리표 | 값 | 뜻 |
|---|---|---|
| `source` | `php@1`, `ts@1`, `schema@1`, `doc:<경로>`, `manual` | 누가 만들었나. 추출기 / 문서 / 사람(curated) |
| `confidence` | `auto` / `verified` | 자동 추출인가, Ken 이 승인했나. **verified 는 Ken 이 날짜 적고 승인한 것뿐** |
| `status` | `active` / `retired` / `missing-from-source` | 살아 있다 / 폐기됐다(레거시 유저웹 1,424개 등) / 승인했었는데 지금 소스에 없다(검토 필요) |
| `sourceRef` | `저장소/경로:줄` | 근거. 에이전트는 답할 때 이걸 인용한다 |

같은 것을 여러 출처가 말하면 **사람 > 문서 > 추출기** 순으로 이긴다. 밀린 값은 버리지 않고 `props.alt` 에 남긴다.

## 5. 어디가 자동이고 어디가 사람 손인가

**자동(추출기)**: 위 그래프의 99%. 스키마·문서·코드에서 기계적으로 뽑는다. 다시 빌드하면 다시 뽑힌다. 틀린 게 있으면 추출기 버그거나 소스가 그런 것이다.

**사람 손(`curated/` 7종)**: 기계가 못 하는 판단. 전부 YAML 이고 Ken 이 승인하면 `verified`.

| 파일 | 담은 판단 | 지금 내용 |
|---|---|---|
| `domains.yaml` | 어느 테이블·라우트·크론이 어느 도메인인가 | order·payment·refund·settlement, 멤버 147 |
| `references.yaml` | 논리 FK — DB 에 FK 가 없어서(502 테이블에 34개뿐) 코드의 조인에서 추론한 것 | 25행, 행마다 근거 줄 |
| `retired.yaml` | 소스엔 있지만 죽은 코드 | 레거시 유저웹(크론용 task/ 제외), addTransactionV2, PayPal, Stripe 지급 |
| `enum-overrides.yaml` | 값의 한글 뜻, 코드 상수 배열 → 컬럼 | `order_status_id` 8개 |
| `queues.yaml` | PHP 상수 ↔ SQS 큐 | `SEND_PUSH_QUEUE` → notif 등 5개 |
| `rules/*.yaml` | 정책 문서를 구현하는 메서드 | 정책 6건, 메서드 73개 |
| `processes/*.yaml` | 업무 흐름 | 주문→결제→확정→이용→취소→정산 6단계 |

이 중 **references·retired·domains 를 Ken 이 승인했다**(2026-10-28). 그게 "승인"의 뜻이다: 기계가 추론한 25개 논리 FK 가 맞다고 Ken 이 보증한 것.

## 6. 직접 써 보기 — 30분

Claude Code 에서 아래 다섯 문장을 그대로 물어보면 된다(MCP `prism-dev` 또는 `prism-local-opdb`). 도구는 에이전트가 고른다. 답에 `sourceRef` 가 붙는지, 자동 추출이라고 말하는지 본다.

1. "`zoom_ms_requestpayment` 테이블에 INSERT 하는 코드가 어디야?" → `kg_code_for_table` — 레거시 `RequestCheckout::createRequest` 가 나와야 한다.
2. "`zoom_transactions` 바꾸면 어느 크론이 영향받아?" → `kg_impact` depth 4 — `updatetransactionfee`, Laravel `remove-duplicate-transactions`.
3. "`confirm-order` 큐 메시지는 누가 보내고 누가 받아?" → `kg_neighbors` PUBLISHES/CONSUMES — 보내는 쪽 7곳, 받는 쪽 `ConfirmOrderService::execute`.
4. "프런트 `createOrder` 에서 `zoom_order` 까지 어떻게 이어져?" → `kg_path` — front → back AccessRule → api `POST /order` → 컨트롤러 → … → 테이블, 7홉.
5. "부분환불 정책은 어떤 코드가 구현해?" → `kg_neighbors` IMPLEMENTS_RULE on `rule:partial-refund` — 메서드 7개(curated).

그다음 **틀린 답을 하나 찾아 보기**. 예를 들어 `kg_code_for_table` 결과 중 하나를 열어 보고 "이 메서드는 그 테이블을 안 쓰는데?" 하는 게 나오면, 그게 7절의 연습 문제다.

## 7. 유지하기 — Ken 의 일

**다시 만들기** (2주마다, 혹은 스키마·정책·큐레이션을 바꿨을 때):

```bash
cd ~/Projects/Zoomzoomtour/Service/zoomtology
scripts/rebuild-and-deploy.sh        # 빌드 → 커밋 → 태그 → 노트북 배포. 내용이 같으면 "건너뜁니다"
```

메인 Mac 의 Prism 둘(dev·pm2)은 README "재빌드법" 의 두 줄로 따로 넣는다.

시작할 때 "경고: <저장소>: …" 가 뜨면 멈추고 그 저장소를 메인으로 돌린다. 빌드는 체크아웃을 그대로 읽어서, 작업 중인 브랜치의 코드가 그래프에 섞이기 때문이다. 그 브랜치가 그래프에 영향이 없다고 확인했으면 그대로 둬도 된다.

**report 읽기** — `build/latest/report.md`. 볼 곳은 네 군데.
- "소스 저장소 경고" — 맨 위에 있으면 메인이 아닌 코드가 섞였을 수 있는 빌드다. 없으면 깨끗하다.
- "이전 빌드 대비" — 뭐가 늘고 줄었나. 이상하게 크게 줄면 추출기나 소스 문제.
- "추출기 report — curated" — 그래프에 없는 uid(큐레이션 오타이거나 소스가 바뀜), 충돌.
- "tombstone" — Ken 이 승인했던 것이 소스에서 사라짐. curated 에서 지우거나 소스를 확인.

**틀린 답 고치기** — 추출기를 고치지 말고 `curated/` 에 한 줄 덮어쓴다(사람 손이 이긴다). 재빌드하면 반영. 추출기 자체 버그는 Jira 로.

## 8. 안 담은 것 · 한계

- 코드 본문·SQL 원문·DDL 기본값·자격증명 — 설계로 뺐다(ADR 0003). kenny 가 Slack 에 그래프 결과를 적어도 코드가 새지 않는 이유.
- 레거시 PHP 에서 헬퍼가 조립하는 SQL 약 600곳은 테이블을 못 뽑았다(report 에 수치). 질문이 거기서 자주 막히면 추출기를 올린다.
- 호출 관계는 메서드 수준이라 `kg_impact` 는 넓게 잡는다. "가능한 영향"이지 확정이 아니다.
- 프런트 페이지 단위, `document-api`, `zoomzoom-chat` 은 없다.
- 부서·역할·업무 프로세스는 다음 슬라이스([next-slice.md](next-slice.md)).

## 9. 용어

| 말 | 뜻 |
|---|---|
| 온톨로지 / 지식그래프 | 여기선 같은 뜻. "무엇이 있고 서로 어떻게 이어지나"를 노드·관계로 적은 것 |
| uid | 노드의 영구 이름. `table:zoom_order` 처럼 `종류:경로` |
| 번들 | 빌드 결과 묶음(tar.gz). 노드·관계 JSONL + manifest + report |
| manifest | 번들의 신분증. 버전·커밋·건수·contentSha256(내용 해시) |
| curated | 사람이 쓰는 YAML 오버레이. 기계 추출 위에 덮인다 |
| 역량 질문(CQ) | "이 그래프가 답해야 하는 질문" 28개. `tests/cq/` 에서 자동으로 확인한다 |
| ADR | 결정 기록. `docs/decisions/` 7건 — 왜 Neo4j 가 아닌지, 왜 번들만 노트북에 가는지 등 |
| Prism kg 도구 | `kg_search` `kg_node` `kg_neighbors` `kg_code_for_table` `kg_tables_for_code` `kg_impact` `kg_path` `kg_bundle_info` |
