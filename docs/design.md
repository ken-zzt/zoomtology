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
| 스키마 | `mysqldump --no-data local_zzt` + 허브 덤프 파싱 | 1단계 |
| 문서 허브 | 프론트매터·status-codes·domains·policies·scheduled-jobs·glossary | 1단계 |
| 레거시 PHP | 정규식 + `$sql` 데이터플로, `load->zoomtu/model` 호출 | 2단계 |
| NestJS·consumer·back·front | ts-morph | 3단계 |
| Laravel | `$table`·Kernel 스케줄 | 3단계 |
| curated | YAML 오버레이 | 4단계 |

## 6. 보안 경계

- 거부 경로·거부 패턴: `schema.yaml` `content_guard`. 빌드(`schema.py`·`guard.py`)와 Prism 로더 두 곳에서 검사.
- 노출 범위(Ken, 2026-10-28): 이름·경로·줄 범위·구조 관계·enum 리터럴·문서 의미 허용. SQL 원문·코드 본문·DDL 기본값·자격증명·env 값 불허. [ADR 0003](decisions/0003-metadata-only.md).
