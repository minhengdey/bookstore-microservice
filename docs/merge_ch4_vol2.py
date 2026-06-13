# -*- coding: utf-8 -*-
"""Volume 2 supplement — async workers, security, deep dives."""
from pathlib import Path
import re

TARGET = Path(__file__).parent / "CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"
MARKER = "## PHỤ LỤC TRIỂN KHAI — CHI TIẾT BỔ SUNG"
INSERT_AFTER = "### P.7 Checklist bảo vệ đồ án — demo live"

VOL2 = r"""
### P.8 Triển khai luồng bất đồng bộ (RabbitMQ + Outbox)

Hệ thống không xử lý mọi side-effect trong request HTTP đồng bộ. Pattern **Transactional Outbox** đảm bảo: ghi DB và publish message nhất quán.

#### P.8.1 Chuỗi payment → shipping

1. Customer POST thanh toán COD → `payment-service` tạo bản ghi `Payment` status SUCCESS/PENDING
2. `payment-outbox-worker` đọc outbox table → publish event `payment.confirmed` lên RabbitMQ
3. `shipping-consumer` nhận message → gọi `shipping-service/internal/shipping/create/`
4. `shipping_db` có bản ghi vận đơn, order status có thể advance qua `order-service` internal API

**Vì sao quan trọng:** Nếu gọi shipping sync trong request thanh toán, timeout shipping sẽ làm user thấy lỗi dù payment đã ghi — trải nghiệm tệ. Async tách **commit business** khỏi **fulfillment**.

#### P.8.2 Chuỗi event → AI (recommender-consumer)

1. `track_behavior` hoặc order purchase tạo tín hiệu
2. Interaction outbox (nếu có) hoặc trực tiếp POST recommender events
3. `recommender-consumer` lắng nghe queue → cập nhật Neo4j node `User`, `Product`, edge `INTERACTED`
4. Lần `GET /recommendations/` tiếp theo reflect graph mới

```mermaid
sequenceDiagram
    participant GW as api-gateway
    participant PAY as payment-service
    participant OB as payment-outbox-worker
    participant MQ as RabbitMQ
    participant SC as shipping-consumer
    participant SH as shipping-service
    participant RC as recommender-consumer
    participant N4 as Neo4j

    GW->>PAY: POST /payments/
    PAY->>OB: outbox row committed
    OB->>MQ: publish payment.confirmed
    MQ->>SC: deliver
    SC->>SH: create shipping
    GW->>MQ: behavior event (parallel)
    MQ->>RC: deliver
    RC->>N4: MERGE nodes/edges
```

#### P.8.3 Workers trong docker-compose

| Worker | Input queue / trigger | Output |
|--------|----------------------|--------|
| `order-outbox-worker` | order events | RabbitMQ publish |
| `payment-outbox-worker` | payment committed | payment events |
| `payment-consumer` | payment events | side effects |
| `shipping-consumer` | payment.confirmed | shipping records |
| `recommender-consumer` | interaction/order events | Neo4j graph |
| `inventory-order-consumer` | order saga (v2) | inventory confirm |
| `dlq-consumer` | dead letters | log/retry |

### P.9 Triển khai bảo mật thực tế

#### P.9.1 NGINX edge (`nginx/nginx.conf`)

- **Rate limit:** `public_api` 30 req/s, `auth_api` 5 req/min — chống brute force login
- **Chặn `/internal/`:** `return 403` — user không thể gọi API nội bộ từ internet
- **Strip headers:** Xóa `X-User-Id`, `X-Role` từ client — chống spoof role
- **auth_request:** Một số route gọi `auth-service/auth/introspect/` trước khi proxy gateway
- **Gzip + keepalive:** Tối ưu bandwidth JSON/HTML

#### P.9.2 JWT session ở BFF

Gateway **không** đưa JWT ra JavaScript. Token nằm `request.session["access_token"]`. Mỗi `_get`/`_post` tới microservice attach `Authorization: Bearer`.

Ưu điểm: giảm XSS đánh cắp token. Nhược điểm: sticky session nếu scale gateway horizontal (cần Redis session — có `redis` container).

#### P.9.3 Service-to-service HMAC

`common/auth.py` và `InternalServicePermission` trong order-service: header `X-Service-Name`, `X-Timestamp`, `X-Service-Signature`. Chỉ container có `INTERNAL_SIGNING_SECRET` mới gọi được `/internal/*`.

### P.10 Phân tích sâu `api-gateway/gateway/views.py`

#### P.10.1 Helper `_get`, `_post`, `_parallel_call`

- `SESSION` requests với connection pool 50 — tránh TCP handshake lặp
- `_parallel_call` dùng `ThreadPoolExecutor` — home load 3 API cùng lúc
- Cache TTL ngắn (10s product, 300s category) — balance freshness vs speed

#### P.10.2 `_recommendation_order_ids`

Hàm trung tâm tích hợp AI catalog:
1. Gọi `GET {recommender}/recommendations/{customer_id}/?limit=N`
2. Parse `recommended_product_ids` hoặc `recommendation_scores`
3. Trả list id đã sort — gateway không tự tính score

#### P.10.3 `_checkout_page_context`

Build context checkout GET: addresses từ user-service, shipping methods, tính subtotal từ cart items hydrate product, apply voucher preview nếu có.

Tách context builder giúp GET và POST error path dùng chung — tránh duplicate template logic.

### P.11 Triển khai cart-service chi tiết

| Operation | HTTP | DB thay đổi |
|-----------|------|-------------|
| Thêm item | POST `/carts/{id}/items/` | INSERT cart_line |
| Tăng SL | PUT item | UPDATE quantity |
| Xóa item | DELETE item | DELETE row |
| Clear sau order | DELETE `/carts/{id}/` | DELETE all items |

Cart gắn `customer_id` (entity_id từ JWT) — không dùng anonymous session cart trên storefront chính.

### P.12 Triển khai order-service legacy — từng bước DB

Khi `POST /orders/`:
1. Validate items, tính `total_amount`, `shipping_fee`, `discount_amount`
2. INSERT `Order`, `OrderItem` rows trong transaction
3. HTTP POST `product-service/internal/reserve-stock/` — giảm `stock` hoặc ghi `InventoryTransaction`
4. Trả order JSON — gateway redirect payment

Status ban đầu thường `PENDING_PAYMENT` hoặc tương đương legacy enum — hiển thị tiếng Việt qua `ORDER_STATUS_VI`.

### P.13 Triển khai interaction-service — review & wishlist

**Review flow:**
1. Gateway kiểm tra order eligible (`DELIVERED`, `COMPLETED`)
2. POST `interaction-service/api/v1/interactions/reviews/` body `{user_id, product_id, rating, comment}`
3. `track_behavior(..., "review")` — weight cao cho recommender

**Wishlist flow:**
1. Toggle `product_wishlist_toggle` POST
2. interaction-service wishlist endpoint
3. `track_behavior(..., "wishlist")`

### P.14 Triển khai promotion-service trong checkout

`checkout_apply_voucher_api` gọi `POST promotion-service/api/promotions/apply-voucher/` với `promotion_code` và cart subtotal.

Response discount_amount → hiển thị realtime trên checkout.html không reload.

Khi submit order, `promotion_code` trong payload order — order-service/promotion consume voucher (tùy implementation legacy).

### P.15 Mô hình dữ liệu — ánh xạ service → database

| Service | Container DB | Bảng chính (khái niệm) |
|---------|--------------|------------------------|
| auth-service | auth-db | User, Role, AuthAudit |
| user-service | user-db | UserProfile, Address |
| product-service | product-db | Product, Category, Brand, Variant |
| cart-service | cart-db | Cart, CartItem |
| order-service | order-db | Order, OrderItem, Outbox |
| payment-service | payment-db | Payment, PaymentMethod |
| shipping-service | shipping-db | Shipping, ShippingMethod, Zone |
| promotion-service | promotion-db | Voucher, FlashSale |
| interaction-service | interaction-db | Interaction, Review, Wishlist, Ticket |
| recommender-ai-service | recommender-db | BehaviorEvent, ModelMetadata |

### P.16 Giải thích RRF (Reciprocal Rank Fusion) trong KB

Trong `hybrid_retriever.py`, sparse (TF-IDF) và dense (embedding) mỗi bên trả ranking riêng. RRF gộp:

\[
score(d) = \sum_{r \in rankings} \frac{1}{k + rank_r(d)}
\]

với `k = HYBRID_RRF_K` (mặc định 60). Công thức này không cần normalize score khác scale — phù hợp hybrid retrieval thực tế.

Sau RRF, `product_reranker` có thể boost theo stock, flash sale, popularity graph.

### P.17 Portal Staff và Admin — triển khai

| Portal | Base URL | File views | Chức năng |
|--------|----------|------------|-----------|
| Staff | `/staff/` | `staff_views.py` | Đơn hàng, KH, tickets |
| Admin | `/admin/` | `admin_views.py` | SP, category, brand, inventory, reports, recommendation |

Đây là Django views riêng — **không** dùng Django admin site mặc định cho toàn bộ (mặc dù từng service có thể có `/admin/` nội bộ).

Admin recommendation gọi recommender MLOps API — xem model version, trigger retrain (nếu configured).

### P.18 Kiểm thử E2E có sẵn trong repo

| Script | Mục đích |
|--------|----------|
| `scripts/e2e_phase_test.py` | Test phase integration |
| `scripts/browser_e2e_test.py` | Browser automation |
| `tests/test_recommender_compose.py` | Recommender trong compose |
| `test_localhost.py` | Smoke test localhost |

Chạy test sau `docker-compose up` xác nhận triển khai không chỉ build được mà còn **hoạt động đúng**.

"""


def main():
    text = TARGET.read_text(encoding="utf-8")
    if "### P.8 Triển khai luồng bất đồng bộ" in text:
        print("Vol2 already merged")
        return
    anchor = INSERT_AFTER
    if anchor not in text:
        raise SystemExit(f"Anchor not found: {anchor}")
    idx = text.index(anchor)
    # insert after P.7 block (find next --- after checklist)
    sub = text[idx:]
    end = sub.find("\n---\n", 0)
    if end == -1:
        raise SystemExit("End marker not found")
    insert_pos = idx + end + len("\n---\n")
    new_text = text[:insert_pos] + "\n" + VOL2 + text[insert_pos:]
    TARGET.write_text(new_text, encoding="utf-8")
    words = len(re.findall(r"\w+", new_text))
    print(f"Merged vol2. Words: {words}, Lines: {len(new_text.splitlines())}")


if __name__ == "__main__":
    main()
