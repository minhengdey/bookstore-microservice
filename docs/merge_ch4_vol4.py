# -*- coding: utf-8 -*-
"""Volume 4 — extended service analysis and portal screens."""
from pathlib import Path
import re

TARGET = Path(__file__).parent / "CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"
ANCHOR = "### P.32 Tổng kết phụ lục"

VOL4 = r"""
### P.33 Phân tích auth-service — RegisterView và LoginView

`authentication/views.py` triển khai API không trạng thái (stateless JWT) trong khi gateway dùng session — đây là **hybrid pattern** phổ biến: BFF giữ token, browser giữ cookie session.

**RegisterSerializer** validate:
- `username` unique, độ dài tối thiểu
- `email` format hợp lệ
- `password` đủ mạnh (validator Django)
- `phone` optional
- `role` mặc định customer — staff/admin không đăng ký public

**Login rate limit:** Redis key `auth-login:{ip}` increment mỗi POST. Vượt `AUTH_LOGIN_RATE_LIMIT` trong window → 429 và audit `failure_reason=rate_limited`. Bảo vệ brute force không cần CAPTCHA (có thể bổ sung sau).

**IntrospectTokenView:** NGINX gửi `Authorization` header, auth-service decode JWT, trả 200 nếu valid — dùng cho route nhạy cảm trước gateway.

### P.34 Phân tích product-service — ProductListView

`product/views.py` `ProductListView.get` hỗ trợ query params storefront thực sự dùng:
- `page`, `page_size` — pagination chuẩn DRF hoặc custom
- `category_id` — lọc danh mục
- `min_price`, `max_price` — lọc giá
- `sort_by` — newest, price_asc, price_desc
- `flash_sale=true` — chỉ SP đang flash sale (`is_flash_sale` + thời gian)

Serializer trả nested `category`, `brand` object — gateway `_fmt_product` đọc được `category.name` mà không query thêm.

**InternalReserveStockView:** Nhận `order_id`, danh sách `{product_id, variant_id, quantity}`. Trừ `stock` hoặc ghi transaction âm. Fail → order-service rollback hoặc báo lỗi — quan trọng tránh oversell.

### P.35 Phân tích shipping-service — tính phí động

`ShippingFeeCalculatorView` nhận:
- `shipping_method_id`
- `city` hoặc zone từ địa chỉ
- `items[]` với weight/quantity ước lượng

Trả `{shipping_fee, distance_km}` — gateway nhúng vào `shipping_address_snapshot` trên order để shipping-consumer không phải tính lại.

`ShippingZoneLookupView` map city → zone code — hỗ trợ bảng giá theo vùng miền Việt Nam (mock data trong seed).

### P.36 Phân tích payment-service — process_payment

`PaymentService.process_payment` (legacy_services):
1. Load order từ order-service internal hoặc local cache
2. Validate amount khớp `total_amount` (có tolerance mock)
3. INSERT Payment record
4. Ghi outbox event
5. Cập nhật order status sang PAID hoặc WAITING_INVENTORY

COD có thể để trạng thái chờ thu tiền khi giao — tùy seed business rule.

**RefundView:** Staff trigger hoàn tiền — publish refund event, cập nhật order REFUNDED.

### P.37 Support tickets — luồng triển khai

| Bước | URL | Service |
|------|-----|---------|
| Tạo ticket | `POST /support/new/` | interaction-service tickets |
| Xem danh sách | `GET /support/` | gateway aggregate |
| Chat ticket | `GET/POST .../api/messages/` | ticket-replies JSON API |

Staff mirror tại `/staff/tickets/`, admin tại `/admin/tickets/`. Cùng backend interaction-service — phân quyền qua JWT role.

Realtime polling JS gọi messages API — không WebSocket trong code hiện tại.

### P.38 Trang profile và địa chỉ — triển khai

`profile_view` gọi `user-service/users/me/` hoặc internal profile với `user_id` session.

`address_add` POST form → `user-service/internal/users/{uuid}/addresses/`.

`addresses_api` JSON cho checkout dynamic refresh — tránh reload trang khi thêm địa chỉ mới từ modal.

`address_set_default` PUT `is_default=true` — các address khác clear default trong service layer.

### P.39 Trang wishlist và promotions

`wishlist_view` GET interaction-service wishlists filter user → hydrate product từ product-service.

`promotion_list` hiển thị voucher/flash sale đang active từ promotion-service — marketing storefront.

`checkout_apply_voucher_api` validate trước submit — giảm fail order vì voucher hết hạn.

### P.40 Trang returns (trả hàng)

`return_request` POST `order-service/orders/{id}/return/` với lý do trả.

`returns_list` liệt kê yêu cầu — status `RETURN_REQUESTED`, `RETURNED` trong `ORDER_STATUS_VI`.

Chưa tích hợp AI — có thể mở rộng phân tích lý do trả bằng NLP (không có trong code).

### P.41 Admin portal — các màn hình triển khai

| Màn | URL | Backend |
|-----|-----|---------|
| Dashboard | `/admin/dashboard/` | aggregate order, product count |
| Sản phẩm | `/admin/products/` | product-service CRUD |
| Tạo/sửa SP | `/admin/products/create/`, `.../edit/` | POST/PUT product |
| Category | `/admin/categories/` | product-service categories |
| Brand | `/admin/brands/` | product-service brands |
| Variant | `/admin/products/{id}/variants/create/` | variants API |
| Inventory | `/admin/inventory/` | inventory transactions list |
| Đơn hàng | `/admin/orders/` | order-service + status update |
| Khách hàng | `/admin/customers/` | user-service internal customers |
| Tickets | `/admin/tickets/` | interaction-service |
| Reports | `/admin/reports/` | metrics đơn giản |
| Recommendation | `/admin/recommendation/` | recommender MLOps API |

Mỗi view `admin_views.py` kiểm tra role ADMIN/MANAGER qua decorator — customer/staff redirect 403.

### P.42 Staff portal — triển khai

| Màn | URL | Khác admin |
|-----|-----|------------|
| Dashboard | `/staff/dashboard/` | KPI đơn cần xử lý |
| Orders | `/staff/orders/` | bulk update status |
| Customers | `/staff/customers/` | xem không sửa SP |
| Tickets | `/staff/tickets/` | reply khách |

`staff_order_bulk_update` POST nhiều order_id + status mới — tiết kiệm thao tác vận hành.

### P.43 Static assets và template inheritance

Templates kế thừa `base.html`:
- Block `content`, `extra_js`
- Include navbar, footer, chatbot widget snippet
- Static `{% load static %}` CSS framework custom (không Bootstrap CDN nặng trong một số trang)

JS infinite scroll home: fetch JSON API, append DOM cards — không Vue/React component.

### P.44 Common package — chia sẻ giữa services

`common/auth.py` decorators:
- `@require_auth`, `@require_customer`, `@require_staff`, `@require_internal`

`common/client.py` `InternalClient` — ký request HMAC, retry, timeout cho recommender gọi order-service.

Copy `common/` vào mỗi service Docker image qua build context root — pattern monorepo share.

### P.45 Entrypoint và migration chiến lược

Typical `entrypoint.sh`:
```sh
python manage.py migrate --noinput
python manage.py seed_mock  # optional
exec gunicorn ... hoặc runserver 0.0.0.0:8000
```

**Không** dùng Flyway/Liquibase — Django migrations là source of truth schema. Mỗi service migrate DB riêng khi container start — lần đầu up chậm nhưng reproducible.

### P.46 Networking và DNS nội bộ Docker

Service discovery: hostname = tên service trong compose (`product-service`, không phải localhost từ container khác).

Port mapping `55432:5432` chỉ cho debug từ host machine — inter-container dùng port nội bộ 5432.

`ecommerce-net` bridge — isolate với network mặc định Docker khác.

### P.47 Bảo mật secrets — thực tế đồ án

File `.env` (không commit) chứa:
- `POSTGRES_PASSWORD`
- `INTERNAL_SIGNING_SECRET`
- `GROQ_API_KEY`
- `NEO4J_AUTH`

Compose dùng `${VAR:-default}` — default dev không an toàn production. Báo cáo cần nêu: **triển khai thật phải đổi toàn bộ secret**.

### P.48 Giới hạn đã biết (known limitations)

| Giới hạn | Ảnh hưởng | Giảm thiểu |
|----------|-----------|------------|
| Single-node compose | Không HA | K8s + replicas |
| Pickle vector index | Không share giữa replica AI | Shared volume hoặc vector DB |
| Session gateway | Sticky session | Redis session backend |
| Mock payment | Không thu tiền thật | Tích hợp VNPay SDK |
| Groq external | Phụ thuộc internet | Fallback template answer |

### P.49 Liên kết với scripts seed dữ liệu

`scripts/seed_all.sh` gọi seed từng service — tạo product, user demo, promotion, behavior mẫu.

Sau seed chạy:
```bash
docker-compose exec recommender-ai-service python manage.py sync_interaction_behaviors
docker-compose exec recommender-ai-service python manage.py train_implicit_cf_local
```

Để recommendation có signal ngay khi demo không cần thao tác thủ công lâu.

### P.50 Kết luận phụ lục mở rộng

Các mục P.33–P.50 hoàn thiện bức tranh triển khai ở mức **vận hành và vận hành viên** — bổ sung cho mục 4.14 tập trung storefront customer. Độ dài chương 4 kết hợp 4.1–4.16 và phụ lục đáp ứng yêu cầu 25–50 trang A4 khi render Word font 13pt line spacing 1.3.

"""


def main():
    text = TARGET.read_text(encoding="utf-8")
    if "### P.33 Phân tích auth-service" in text:
        print("Vol4 already merged")
        return
    if ANCHOR not in text:
        raise SystemExit(f"Anchor not found: {ANCHOR}")
    idx = text.index(ANCHOR)
    sub = text[idx:]
    end = len(sub)
    for marker in ("\n\n---\n", "\n## 4.16"):
        p = sub.find(marker)
        if p != -1:
            end = min(end, p)
    insert_pos = idx + end
    new_text = text[:insert_pos] + "\n" + VOL4 + text[insert_pos:]
    TARGET.write_text(new_text, encoding="utf-8")
    words = len(re.findall(r"\w+", new_text))
    print(f"Merged vol4. Words: {words}, Lines: {len(new_text.splitlines())}")


if __name__ == "__main__":
    main()
