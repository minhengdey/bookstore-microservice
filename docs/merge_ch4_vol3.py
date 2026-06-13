# -*- coding: utf-8 -*-
"""Volume 3 — extended walkthroughs per microservice."""
from pathlib import Path
import re

TARGET = Path(__file__).parent / "CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"
ANCHOR = "### P.18 Kiểm thử E2E có sẵn trong repo"

VOL3 = r"""
### P.19 Walkthrough đăng nhập — từng dòng request

**Bước 1:** Browser `POST /login/` form body `username`, `password`, `login_type=customer`.

**Bước 2:** `login_view` không validate business — chuyển tiếp auth-service.

**Bước 3:** `LoginView.post` → `AuthService.login()`:
- Tra cứu user theo username
- `check_password` Django hash
- Kiểm tra role customer có trong `user.roles`
- `TokenService` sinh access (ngắn hạn) + refresh (dài hơn)
- Ghi `AuthAudit` success=True

**Bước 4:** Gateway nhận JSON, set session, `redirect("home")`.

**Bước 5:** Browser `GET /` cookie session → `home()` nhận diện role customer → gọi recommender.

Điểm hay bị hỏi bảo vệ: **JWT ở đâu?** — Trong session server-side, không trong localStorage.

### P.20 Walkthrough checkout — validation layers

| Layer | File | Kiểm tra |
|-------|------|----------|
| 1. Gateway form | `checkout` POST | address_id, shipping_method_id, session user |
| 2. Address resolve | `_resolve_user_address` | address thuộc user, chưa xóa |
| 3. Address snapshot | `_validate_shipping_address_snapshot` | phone, city, line không rỗng |
| 4. Shipping fee | `_fetch_shipping_fee` | shipping-service trả fee hợp lệ |
| 5. Cart items | loop order_items | product_id, quantity>0, unit_price>0 |
| 6. Order service | `OrderListCreateView` | stock, promotion, persist |

Mỗi layer fail → render lại `checkout.html` với `error` string tiếng Việt — không throw 500 cho user.

### P.21 `behavior_tracking.py` — hợp đồng event

Payload gửi recommender:

```json
{
  "customer_id": 12,
  "product_id": 45,
  "action": "view",
  "session_id": "django_session_key",
  "device": "desktop",
  "persona": "customer"
}
```

Action alias được chuẩn hóa (`cart_add` → `add_to_cart`). Unsupported action log warning, return False — không crash trang.

Interaction bus nhận `event_type` UPPERCASE (`VIEW`, `PURCHASE`). `idempotency_key` UUID tránh duplicate khi retry.

### P.22 RecommenderService — giải thích chiến lược hybrid

**Implicit CF:** Ma trận sparse user-item từ events → ALS train → predict score item chưa tương tác.

**Co-occurrence:** User A và B cùng view nhiều SP → gợi ý SP B thích cho A.

**Co-purchase:** Từ `recommender-orders` — ai mua X thường mua Y.

**Category affinity:** User tích lũy điểm category từ behavior → gợi ý SP mới cùng category.

**Fallback:** Popular trong category hoặc global khi cold start.

`strategy` string trong API response cho biết nhánh nào dominate — hữu ích debug demo.

### P.23 `build_catalog_index` — quy trình ops

```bash
docker-compose exec recommender-ai-service python manage.py build_catalog_index --force
```

1. `get_hybrid_retriever()` singleton
2. `_fetch_all_products()` paginate product-service
3. Build TF-IDF matrix + encode embeddings (có thể mất vài phút lần đầu)
4. Pickle write `catalog_hybrid_index.pkl`
5. Chatbot retrieval dùng file này — **không cần rebuild mỗi request**

Nếu skip rebuild khi catalog count không đổi — tiết kiệm thời gian startup.

### P.24 Chatbot `rag_llm.py` — cấu trúc prompt (khái niệm)

Prompt assembly (không trích full API key):
1. System role: trợ lý bán hàng tiếng Việt, chỉ dùng context
2. User history: vài turn gần nhất từ `history[]` client gửi
3. Retrieved products: tên, giá, mô tả từ hybrid retriever
4. Graph snippet: từ GraphRepository
5. User message hiện tại

Groq trả completion → parse `answer`, đính kèm `products` array cho UI.

`recent_behaviors` optional — boost SP liên quan hành vi gần đây.

### P.25 Catalog-service và Inventory-service — trạng thái triển khai

Hai service **đã deploy** trong compose với DB riêng, API REST đầy đủ:
- `catalog-service`: brands, categories, products, variants, images, reviews
- `inventory-service`: reserve, confirm, release, adjust stock

`OrderSagaManager.start_checkout` trong order-service v2 điều phối saga — nhưng `api-gateway/checkout` **chưa** gọi endpoint này.

**Kế hoạch nối BFF (gợi ý mở rộng, chưa code):**
1. Sửa `checkout` POST target `order-service/api/v1/orders/checkout/`
2. Map cart items sang catalog variant ids
3. UI giữ nguyên — chỉ đổi backend orchestration

Ghi rõ trong báo cáo để hội đồng không hỏi "sao thiết kế SAGA mà code không dùng".

### P.26 Notification-service

Container có trong compose (`notification-service`, `notification-db`). Code gửi notification qua outbox/event — storefront **không** hiển thị center thông báo push đầy đủ. Email/SMS **không tìm thấy** provider thật (SMTP SendGrid) trong env mẫu.

### P.27 Model-serving-service

Container `model-serving-service` — mock phục vụ GNN/embedding serving tách biệt. Recommender có thể gọi qua HTTP nội bộ tùy env. Đồ án demo chủ yếu load model in-process trong recommender container.

### P.28 Redis usage cụ thể

| Use case | Service |
|----------|---------|
| Auth login rate limit | auth-service cache |
| Gateway session (nếu configured) | api-gateway |
| Order saga lock / state | order-redis |
| Recommender cache | recommendation_pipeline redis_client |

Không phải tất cả đều bắt buộc cho happy path demo — nhưng production cần Redis HA.

### P.29 Jaeger tracing

Container `jaeger` expose UI trace — service gửi span nếu configure OpenTelemetry. Dev local có thể bỏ qua; vẫn có `X-Request-Id` header xuyên suốt để log correlation.

### P.30 Ma trận phụ thuộc container (depends_on)

Gateway `depends_on` auth, product, cart, order... với `condition: service_healthy`. Điều này giải thích lần đầu `docker-compose up` mất 2–5 phút — đợi migrate + seed entrypoint.

Entrypoint mỗi service: `migrate` → optional `seed_mock` → `runserver`/`gunicorn`.

### P.31 Hướng dẫn đọc code cho người mới

**Luồng mua hàng:** `urls.py` → `checkout` → trace `_post` tới `order-service` → đọc `order/views` legacy.

**Luồng AI:** `behavior_tracking` → `recommender/events` → `recommender_service.recommend`.

**Luồng chat:** `ai_chat_proxy` → `rag_views` → `hybrid_retriever` + `rag_llm`.

Đọc theo vertical slice một lần hiểu hơn đọc từng folder service cô lập.

### P.32 Tổng kết phụ lục

Phụ lục P.1–P.32 bổ sung chi tiết vận hành, bảo mật, async, và đọc code — phần mà các mục 4.1–4.16 đã giới thiệu ở mức kiến trúc. Kết hợp đọc song song với source tree trên máy local đạt hiệu quả cao nhất.

"""


def main():
    text = TARGET.read_text(encoding="utf-8")
    if "### P.19 Walkthrough đăng nhập" in text:
        print("Vol3 already merged")
        return
    if ANCHOR not in text:
        raise SystemExit(f"Anchor not found: {ANCHOR}")
    idx = text.index(ANCHOR)
    # find end of P.18 section (next blank line before --- or end)
    sub = text[idx:]
    end = sub.find("\n\n### P.", len("### P.18"))
    if end == -1:
        end = len(sub)
    insert_pos = idx + end
    new_text = text[:insert_pos] + "\n" + VOL3 + text[insert_pos:]
    TARGET.write_text(new_text, encoding="utf-8")
    words = len(re.findall(r"\w+", new_text))
    print(f"Merged vol3. Words: {words}, Lines: {len(new_text.splitlines())}")


if __name__ == "__main__":
    main()
