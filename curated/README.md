# curated — 사람이 쓰는 오버레이

자동 추출 위에 얹는다. 병합 우선순위 **manual > doc > extractor**, 밀린 값은 `props.alt.<source>` 에 남는다([ADR 0005](../docs/decisions/0005-curated-overlay-and-governance.md)).
로더는 `extractors/zoomtology/curated.py`. 파일 머리의 `confidence`(auto|verified)·`lastVerifiedAt`·`verifiedBy` 가 기본값이고 항목에서 덮어쓸 수 있다.
**`verified` 는 Ken 이 그 행을 승인했다는 뜻**이라 날짜 없이는 적용하지 않는다(report 에 남김). 에이전트가 초안을 쓸 때는 `auto` 로 둔다. uid 는 [`ontology/uid.md`](../ontology/uid.md).

| 파일 | 내용 | 문법 |
|---|---|---|
| `domains.yaml` | Domain 노드 + BELONGS_TO_DOMAIN | `domains[].members[]` = uid 또는 `{glob, label}` |
| `references.yaml` | 논리 FK `REFERENCES {kind: logical, evidence}` | `references[] {from, to, evidence[], note}` (참조하는 컬럼 → PK) |
| `retired.yaml` | 폐기 플래그 + SUPERSEDES | `retired[] {name, reason, evidence, uids[] | match[] {uid_glob | label+props}, except[], supersededBy}` — 폐기 노드에 닿는 관계도 retired |
| `enum-overrides.yaml` | 코드 enum 배열 → 컬럼(`arrays`, php.py 가 읽음), 의미 보정(`values`) | `values[] {column, values: {값: {meaning, label, note}}}` |
| `queues.yaml` | PHP `SEND_*_QUEUE` ↔ 큐 역할(php.py 가 읽음) | `constants: {상수: 역할}` |
| `rules/<slug>.yaml` | 정책 문서 → 유닛 수준 IMPLEMENTS_RULE | `rule, units[] {uid, role, section}` |
| `processes/<slug>.yaml` | 프로세스. v1 은 Doc 노드 + 단계별 DOCUMENTED_BY | `uid, title, steps[] {id, name, actor, refs[]}` |

빌드 report(`build/latest/report.md` "추출기 report — curated")에 그래프에 없는 uid·충돌(FK 방향·enum 의미 불일치·supersede 대상 없음)·적용하지 않은 항목이 남는다. 그래프에 없는 uid 는 오타이거나 소스가 바뀐 것이다.
