# curated — 사람이 쓰는 오버레이

자동 추출 위에 얹는다. 병합 우선순위 **manual > doc > extractor**, 밀린 값은 `props.alt.<source>` 에 남는다([ADR 0005](../docs/decisions/0005-curated-overlay-and-governance.md)).
모든 항목은 `source: manual`, `confidence: verified`, `lastVerifiedAt`(필수), `verifiedBy`(선택)를 갖는다. uid 는 [`ontology/uid.md`](../ontology/uid.md).

| 파일 | 내용 | 채우는 단계 |
|---|---|---|
| `domains.yaml` | Domain 노드 + BELONGS_TO_DOMAIN | 4 |
| `references.yaml` | 논리 FK (`REFERENCES {kind: logical}`), 행마다 근거 | 4 |
| `retired.yaml` | 폐기 플래그 + SUPERSEDES (admin/catalog, addTransactionV2, PayPal, Stripe destination) | 4 |
| `enum-overrides.yaml` | enum 의미 보정·추가, 코드 enum 배열 → 컬럼 매핑 | 4 |
| `queues.yaml` | PHP `SEND_*_QUEUE` 상수 ↔ 큐 역할 (Ken 제공) | 4 |
| `rules/*.yaml` | 정책 문서 → 코드 유닛 IMPLEMENTS_RULE (유닛 수준) | 4 |
| `processes/order-to-settlement.yaml` | 파일럿 프로세스. v1 은 Doc 노드로 내보냄 | 4 |

문법(`add` / `override` / `supersede`)은 4단계에 `curated.py` 와 함께 확정한다. 그 전엔 이 디렉터리는 비어 있다.
