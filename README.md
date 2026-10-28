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

추출·빌드·배포 명령은 1~4단계(ZDV-345~348)에서 붙는다. 빌드는 **Ken 의 메인 Mac** 에서만 돌린다(형제 저장소 `../` 를 읽는다). 노트북(mbp2017)엔 번들만 보낸다 — [ADR 0002](docs/decisions/0002-git-source-laptop-gets-bundles.md).

## 규칙

- 이 저장소는 `zoomzoom-services/tools/repos.tsv`·워크스페이스 저장소 지도에 넣지 않고, mbp2017 의 `Service/` 에 clone 하지 않는다.
- 추출기는 `schema.yaml` 의 `deny_paths` 를 읽지 않고, 모든 prop 값은 `deny_patterns` 를 통과해야 한다. 걸리면 빌드 실패.
- uid 는 손으로 조립하지 않는다 — `extractors/zoomtology/model.py` 의 생성기를 쓴다.
- 문서 규약은 `zoomzoom-services/CONVENTIONS.md`.
