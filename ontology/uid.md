# uid 규칙

그래프의 모든 노드는 **절대 바뀌지 않는 소문자 ASCII 식별자 `uid`** 를 가진다. 사람이 읽는 이름(`name`, `nameKo`)은 바뀌어도 `uid` 는 그대로다.
추출기·큐레이션 파일·Prism 도구·테스트는 전부 이 규칙에 맞춰 uid 를 만들고 찾는다. 정규식은 [`schema.yaml`](schema.yaml) 의 `labels.<Label>.uid` 가 원본이다.

## 형식

`<prefix>:<path>` — prefix 는 라벨마다 하나. path 안의 구분자는 라벨별로 정해져 있다(아래 표).
저장소 이름은 `zoomzoom-services/tools/repos.tsv` 의 `name` 을 그대로 쓴다. 파일 경로는 저장소 루트 기준, `/` 구분, 확장자 포함.

| Label | prefix | 형식 | 예 |
|---|---|---|---|
| Repo | `repo:` | `repo:<name>` | `repo:zoomzoom-api` |
| Service | `svc:` | `svc:<repo>/<instance>` | `svc:message-consumer/order`, `svc:zoomzoom-api/prod-back`, `svc:zoomzoom-api/mq` |
| Module | `module:` | `module:<repo>/<path>#<Symbol>` 또는 `module:<repo>/<dir>` | `module:zoomzoom-api/src/order/order.module.ts#OrderModule`, `module:zoomzoom-admin/admin/controller` |
| File | `file:` | `file:<repo>/<path>` | `file:zoomzoom-admin/system/library/zoomtu/order_info.php` |
| CodeUnit | `code:` | `code:<repo>/<path>#<Class>::<method>` / `#<function>` / `#<Class>` | `code:zoomzoom-admin/system/library/zoomtu/order_info.php#ZZTOrderInfo::getOrder` |
| Route | `route:` | `route:<repo> <METHOD> <path>` (HTTP), `route:<repo> route=<a/b/c>` (OpenCart, 소문자), `route:<repo> <METHOD> <regex>` (back AccessRule) | `route:zoomzoom-api PATCH /order/:id/rejected`, `route:zoomzoom-admin route=cron/tasks/statuscheck` |
| Queue | `queue:` | `queue:<role>` | `queue:order` (email · entity · order · notif · event) |
| QueueMessage | `msg:` | `msg:<role>/<key>` — key 는 enum 의 문자열 값 | `msg:order/confirm-order` |
| CronJob | `cron:` | `cron:<host>/<route-or-command>` | `cron:admin/cron/tasks/statusCheck`, `cron:mq/task/product/discount-price`, `cron:zoomzoom-auth/zzt-cron:confim-mileage` |
| Database | `db:` | `db:<handle>` | `db:zzt`, `db:stats`, `db:numbers`, `db:iso`, `db:wc` |
| Table | `table:` | `table:<name>` (기본 DB) / `table:<db>/<name>` | `table:zoom_order`, `table:iso/xxx` |
| Column | `col:` | `col:<table>.<column>` | `col:zoom_order.order_status_id` |
| EnumValue | `enum:` | `enum:<table>.<column>=<value>` | `enum:zoom_ms_requestpayment.status_id=7` |
| BusinessRule | `rule:` | `rule:<slug>` — 정책 문서 파일명 stem | `rule:partial-refund` |
| Domain | `domain:` | `domain:<slug>` | `domain:settlement` |
| ExternalService | `ext:` | `ext:<slug>` | `ext:iamport`, `ext:viator`, `ext:sqs` |
| Doc | `doc:` | `doc:<repo>/<path>` (+ `#<section>`) | `doc:zoomzoom-services/docs/20-database/policies/partial-refund.md`, `…/order.md#zoom_order` |

### 예약 (1차엔 쓰지 않음)

`dept:`, `role:`, `process:`, `person:` — 부서·역할·업무 프로세스·사람. 추출기는 이 접두사를 만들지 않는다.

## 규칙

1. **대소문자**: prefix 와 path 의 구분자는 소문자. 코드 심볼(`ZZTOrderInfo`, `OrderModule`)과 HTTP 메서드(`PATCH`)는 코드에 있는 그대로 둔다.
2. **공백**: Route 만 공백을 쓴다(`<repo> <METHOD> <path>`). 다른 라벨은 공백 금지.
3. **폐기된 자산의 uid 는 재사용하지 않는다.** `status: retired` 로 남기고 새 uid 를 만든다.
4. **이름이 바뀌면** 새 uid 를 만들고 `SUPERSEDES` 관계로 잇는다. uid 를 고쳐 쓰지 않는다.
5. **한글은 uid 에 넣지 않는다.** `nameKo`, `summary` 에 넣는다.
6. 테이블 접두사 `zoom_` 은 떼지 않는다(`provider_product` 처럼 접두사 없는 테이블이 있어서 떼면 충돌).
7. OpenCart 라우트는 `route=` 뒤에 `폴더/파일/메서드` 를 **소문자**로 쓴다(PHP 메서드 이름은 대소문자를 가리지 않아 crontab·문서·코드 표기가 제각각이다. 코드 표기는 `props.path` 에 남긴다). `index` 메서드는 `폴더/파일` 로도 등록한다.
8. 큐 메시지 key 는 `SQS<Role>ServiceKey` enum 의 **값**(`'confirm-order'`)이지 멤버 이름(`ConfirmOrder`)이 아니다. 멤버 이름은 `props.enumName` 에 둔다.
