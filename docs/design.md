---
type: design
status: draft
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - ontology/schema.yaml
  - ontology/uid.md
tags: [zoomtology, design]
related_to:
  - decisions/index.md
  - competency-questions.md
---

# zoomtology 설계 (v1)

> 1차 계획서 전문은 Jira 에픽 ZDV-343 첨부 `zoomtology-plan-2026-10-28.md`. 이 문서는 구현하면서 맞는 쪽으로 갱신한다. 단계별 상세는 각 단계가 끝날 때 채운다.

## 1. 한 문장

줌줌투어의 **DB 테이블 ↔ 서비스 코드 ↔ 실행 진입점(라우트·큐·크론)** 관계를 Git 원본에서 빌드한 그래프로 만들고, Agent Prism 의 MCP 도구 `kg_*` 로 에이전트(Claude Code·Codex·kenny)가 읽기 전용으로 조회한다. 그래프엔 메타데이터만 있고 코드 본문은 없다.

## 2. 흐름

```
Service/ 저장소들 ─┐
문서 허브 docs ────┼─ extractors/ (Python·ts-morph) ─▶ build.py ─▶ build/dist/zoomtology-<v>.tar.gz
스키마 덤프 ──────┤        ▲                              │           (manifest + nodes.jsonl + edges.jsonl + report.md)
curated/*.yaml ───┘        │ ontology/schema.yaml 로 검증    ▼
                                                 Prism `kg load` (Mac dev :4300 / local-opdb :4100 / mbp2017 :4100)
                                                          ▼
                                      /mcp 도구 kg_search·kg_node·kg_neighbors·kg_impact·kg_tables_for_code·kg_code_for_table·kg_path·kg_bundle_info
                                                          ▼
                                      Claude Code (prism-dev / prism-local-opdb) · kenny (prism-laptop)
```

## 3. 온톨로지

원본: [`ontology/schema.yaml`](../ontology/schema.yaml) (라벨 17·관계 20·거버넌스·content guard), [`ontology/uid.md`](../ontology/uid.md).
왜 이렇게인지: [ADR 0001~0007](decisions/index.md).

## 4. 저장 (Prism `prism` DB) — 1단계에서 확정

`kg_bundle`(version·git_sha·status loading|active|previous|discarded·counts·manifest) · `kg_node`(bundle_id, uid, label, name, summary, search_text FULLTEXT ngram, props JSON, 거버넌스 컬럼) · `kg_edge`(bundle_id, from_uid, to_uid, type, props JSON, 거버넌스). 새 bundle_id 로 적재 → 검증 → 트랜잭션 하나로 active 교체. DDL 없음(앱 계정은 DML 만).

## 5. 추출기 — 2·3단계에서 확정

| 출처 | 방법 | 상태 |
|---|---|---|
| 스키마 | `mysqldump --no-data local_zzt`(`build/inputs/`, gitignore) + 허브 덤프 파싱. 허브에만 있는 테이블·컬럼은 `missing-from-source`. 코멘트의 `0: 대기, 1: 완료`·`a, b, c` 꼴은 EnumValue(origin ddl-comment) | **완료** (`schema_ddl.py`) |
| 문서 허브 | 모든 `docs/**/*.md`→Doc, 프론트매터 `sources`→DOCUMENTED_BY(File/Module placeholder), status-codes→EnumValue(origin status-codes, doc 우선), domains→Column.meaning, policies→BusinessRule+IMPLEMENTS_RULE(파일 수준), scheduled-jobs→CronJob+TRIGGERS(admin/mq/auth 3개 표), glossary→Table.aliases, table-ownership→usageByRepo, repos.tsv→Repo. AgentPrism tables.yaml→piiRule(`classification.py`) | **완료** (`docs.py`) |
| 레거시 PHP | 정규식 + `$sql` 데이터플로, `load->zoomtu/model` 호출 | 2단계 |
| NestJS·consumer·back·front | ts-morph | 3단계 |
| Laravel | `$table`·Kernel 스케줄 | 3단계 |
| curated | YAML 오버레이 | 4단계 |

### 빌드 (`build.py`, `zoomtology build`)

1. 추출기 순서: schema → classification → docs (뒤 단계에서 php → ts → laravel → curated).
2. `Collector` 가 uid 로 병합. 값 우선순위 manual > doc > extractor. 노드의 `source`/`sourceRef` 는 처음 만든 쪽(보통 추출기)을 유지하고, 밀린 값은 `props.alt[<source>]`, 문서 근거는 `props.docRefs[]`. 부분 레코드(`partial=True`)는 노드가 없으면 버리고 report 에 적는다.
3. 노드가 없는 관계는 버리고 report(`노드가 없어 버린 관계`)에 적는다 — 문서 부패 또는 아직 없는 추출기.
4. `state/first-seen.tsv` 로 `firstSeenAt`, `state/uids.txt` 와 비교해 사라진 uid 를 report.
5. `schema.yaml` 로 전부 검증(실패하면 번들을 쓰지 않는다).
6. `build/dist/zoomtology-<UTC시각>-<sha7>[-dirty].tar.gz` (manifest.json·nodes.jsonl·edges.jsonl·report.md, 정렬·결정적) + `build/latest/` + state 갱신.

첫 번들(2026-10-28, `ee17d6b`): 노드 5,434 · 관계 5,577 · 0.75초.

## 6. 보안 경계

- 거부 경로·거부 패턴: `schema.yaml` `content_guard`. 빌드(`schema.py`·`guard.py`)와 Prism 로더 두 곳에서 검사.
- 노출 범위(Ken, 2026-10-28): 이름·경로·줄 범위·구조 관계·enum 리터럴·문서 의미 허용. SQL 원문·코드 본문·DDL 기본값·자격증명·env 값 불허. [ADR 0003](decisions/0003-metadata-only.md).
