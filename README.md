# zoomtology — 줌줌투어 지식그래프

줌줌투어의 **DB 테이블 ↔ 서비스 코드 ↔ 실행 진입점(라우트·큐·크론)** 관계를 코드·스키마·문서에서 추출해 그래프로 만들고,
[Agent Prism](https://github.com/ken-zzt/AgentPrism) 의 MCP 도구 `kg_*` 로 AI 에이전트(Claude Code·Codex·kenny)가 읽기 전용으로 조회하게 한다.
그래프에는 **메타데이터(이름·위치·관계·의미)만** 있다. 코드 본문·SQL 원문·비밀 값·실데이터는 넣지 않는다.

이 저장소가 원본이다. 그래프 DB(Prism MySQL)는 여기서 언제든 다시 만드는 산출물이다. 진행: Jira 에픽 **ZDV-343**.

## 구성

| 경로 | 내용 |
|---|---|
| `ontology/schema.yaml`, `ontology/uid.md` | 온톨로지 원본 — 라벨·관계·속성·uid 규칙·content guard |
| `extractors/` | Python 패키지 `zoomtology`(검증기·추출기 schema_ddl/classification/docs/php/laravel/ts·빌드) + `ts/`(node + ts-morph, NestJS 계열 → JSONL) |
| `curated/` | 사람이 쓰는 오버레이 YAML(도메인·논리 FK·폐기·enum 보정·규칙·파일럿 프로세스) |
| `state/` | 드리프트 추적(`first-seen.tsv`, `uids.txt`) |
| `build/latest/` | 마지막 빌드의 `manifest.json`·`report.md`(커밋). 번들 tar.gz 는 `build/dist/`(커밋 안 함) |
| `scripts/` | `build.sh`, `deploy-laptop.sh`, `rebuild-and-deploy.sh` |
| `docs/` | [설계](docs/design.md)·[ADR](docs/decisions/index.md)·[역량 질문](docs/competency-questions.md)·사전조사 PDF |
| `tests/` | pytest(fixture/golden), `cq/`(Prism 도구 회귀) |

## 실행

```bash
cd extractors
uv sync --extra dev                 # Python 3.12+, uv
uv run pytest -q                    # 스키마 검증기 테스트
uv run zoomtology validate ../tests/fixtures/nodes.jsonl ../tests/fixtures/edges.jsonl
uv run zoomtology build               # 추출 → 병합 → 검증 → build/dist/*.tar.gz + build/latest/ + state/
```

NestJS 계열(zoomzoom-api 등 6개)은 `extractors/ts`(node 24 + ts-morph)가 읽는다. 처음 한 번 `cd extractors/ts && npm install`.
빌드가 저장소마다 `node src/extract.mjs` 를 돌려 `build/inputs/ts/<repo>.jsonl` 을 만든다(약 10초). `ZOOMTOLOGY_TS_CACHE=1` 이면 있는 JSONL 을 재사용한다.

재빌드·배포는 스크립트 하나로 한다(메인 Mac 에서만 — 형제 저장소 `../` 를 읽는다). 노트북(mbp2017)엔 번들만 보낸다 — [ADR 0002](docs/decisions/0002-git-source-laptop-gets-bundles.md).

```bash
scripts/rebuild-and-deploy.sh             # build.sh → build/latest·state 커밋 → 태그 bundle/<version> → deploy-laptop.sh
scripts/deploy-laptop.sh build/dist/zoomtology-<version>.tar.gz   # 번들만 다시 올릴 때
```

dev Prism(메인 Mac :4300)에 올릴 땐 `AgentPrism` 에서 `yarn kg:load <번들>`. 역량 질문 회귀는 `tests/cq/run_cq.py --stage N` (README 의 실행 절).

## 조회법 (에이전트용)

Prism MCP 의 `kg_*` 8개. 먼저 `kg_search` 로 uid 를 찾고 그 uid 로 나머지를 부른다. 결과는 메타데이터뿐이고 코드 본문·SQL 은 없다.

| 묻고 싶은 것 | 도구 | 예 |
|---|---|---|
| 이름으로 찾기 | `kg_search {q, label?, limit?}` | `{q: "zoom_order", label: "Table"}` → `table:zoom_order` |
| 노드 상세·근거 문서·enum 값 | `kg_node {uid}` | `{uid: "col:zoom_ms_requestpayment.status_id"}` → 값 22개와 의미 |
| 이웃 | `kg_neighbors {uid, direction?, types?, labels?, depth≤2}` | `{uid: "rule:partial-refund", direction: "in", types: ["IMPLEMENTS_RULE"]}` |
| 테이블을 읽고 쓰는 코드 | `kg_code_for_table {table, op? read\|write\|join, repo?}` | `{table: "zoom_order", op: "write", repo: "zoomzoom-admin"}` |
| 코드가 닿는 테이블(피호출자까지) | `kg_tables_for_code {uid \| "repo/path#Sym", depth≤2}` | `{uid: "zoomzoom-api/src/order/application/commands/confirm-order.command.ts#ConfirmOrderCommand::execute"}` |
| 바꾸면 영향받는 라우트·크론·큐 | `kg_impact {uid, depth≤4}` | `{uid: "table:zoom_transactions", depth: 4}` — "가능한 영향"이지 확정이 아니다 |
| 두 노드 사이 경로 | `kg_path {from, to, maxDepth≤8, types?}` | 프런트 함수 → 테이블: `types: ["CALLS_HTTP","HANDLES","CALLS","READS","WRITES"]` |
| 그래프 버전 | `kg_bundle_info {}` | version·gitSha·builtAt — 최신인지 물으면 이걸로 답한다 |

uid 규칙은 [`ontology/uid.md`](ontology/uid.md). `confidence: auto` 는 자동 추출, `verified` 는 Ken 이 승인한 것. `status: retired` 는 폐기된 코드라 지금 동작의 근거로 쓰지 않는다.
답할 때는 `sourceRef`(`저장소/경로:줄`)를 근거로 적는다.

## 큐레이션법

`curated/*.yaml` 을 고치고 다시 빌드하면 된다([curated/README.md](curated/README.md)). 요령:

- 틀린 관계·의미를 발견하면 추출기를 고치기 전에 curated 로 덮는다(manual 이 이긴다). 추출기 수정은 다음 빌드에서 같이.
- 새 항목은 `confidence: auto` 로 넣고, Ken 이 보고 맞으면 `verified` + `lastVerifiedAt` + `verifiedBy: ken`. verified 는 날짜 없이는 적용되지 않는다.
- 빌드 report 의 "추출기 report — curated" 에 그래프에 없는 uid·충돌이 남는다. 없는 uid 는 오타이거나 소스가 바뀐 것.
- verified 였던 노드가 소스에서 사라지면 다음 빌드가 `missing-from-source` tombstone 으로 남기고 report 에 적는다 — curated 에서 지우거나 소스를 확인한다.

## 재빌드법

```bash
# 0. (가끔) 스키마 덤프 갱신 — build.sh 가 90일 넘으면 경고한다
zzt-env exec mysql mysqldump --no-data -uroot local_zzt > build/inputs/local_zzt-$(date +%F).sql
# 1. 빌드 → 커밋 → 태그 → 노트북 배포. 그래프 내용(contentSha256)이 안 바뀌었으면 커밋·배포를 건너뛴다
scripts/rebuild-and-deploy.sh
# 2. 메인 Mac 의 Prism 들에도 올릴 때
(cd ../../AgentPrism && yarn kg:load ../Service/zoomtology/build/dist/zoomtology-<version>.tar.gz)   # dev :4300
(cd ~/apps/agent-prism && node dist/kg/cli.js load /…/zoomtology-<version>.tar.gz)                   # pm2 :4100
# 3. 회귀
PRISM_URL=http://localhost:4300/mcp PRISM_TOKEN=prt_… uv run --project extractors python tests/cq/run_cq.py --stage 4
```

번들 보관(Ken 결정 2026-10-28): **태그만** — `bundle/<version>` 태그 + 커밋된 `build/latest`·`state` 로 재현한다. `build/dist/*.tar.gz` 는 로컬(gitignore), 노트북은 `var/kg/` 최근 5개. GitHub release·JSONL 커밋은 하지 않는다. 재빌드 주기: 스키마 덤프를 갱신했을 때·큐레이션을 바꿨을 때, 그 밖엔 2주마다.

`build/latest/report.md` 의 "이전 빌드 대비" 표로 무엇이 늘고 줄었는지 본다. `manifest.json` 의 `contentSha256` 이 같으면 입력이 안 바뀐 것이다(날짜 거버넌스는 제외).

## 규칙

- 이 저장소는 `zoomzoom-services/tools/repos.tsv`·워크스페이스 저장소 지도에 넣지 않고, mbp2017 의 `Service/` 에 clone 하지 않는다.
- 추출기는 `schema.yaml` 의 `deny_paths` 를 읽지 않고, 모든 prop 값은 `deny_patterns` 를 통과해야 한다. 걸리면 빌드 실패.
- uid 는 손으로 조립하지 않는다 — `extractors/zoomtology/model.py` 의 생성기를 쓴다.
- 문서 규약은 `zoomzoom-services/CONVENTIONS.md`.
