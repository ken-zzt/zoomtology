---
type: database
status: active
sources: []
---

# 상태값

### `zoom_order.order_status_id`

| 값 | 의미 |
|---|---|
| 0 | 문의중 |
| 1 | **예약요청** |

### `zoom_product.payment_type` / `zoom_ms_requestpayment.payment_type`

| 값 | 라벨 | 의미 |
|---|---|---|
| `card` | 카드 | 카드 결제 |

### `zoom_transactions.kind` — 파트너 청구 관련

| kind | `reference_type` | 생기는 때 |
|---|---|---|
| `seller_charge` | `seller_charge` | 청구가 기록될 때 |
