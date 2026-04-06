# Bookstore Microservice — API Documentation

**Base URL (user-facing):** `http://localhost:8000` (API Gateway)

Các service backend chạy trên port riêng; Gateway proxy request xuống từng service. Auth: JWT (Bearer token) hoặc session (Gateway).

---

## 1. API Gateway `:8000`

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/` | Trang chủ |
| GET | `/login/` | Form đăng nhập |
| POST | `/login/` | Đăng nhập |
| GET | `/logout/` | Đăng xuất |
| GET | `/register/` | Form đăng ký |
| POST | `/register/` | Đăng ký khách hàng |
| GET | `/books/` | Danh sách sách |
| GET/POST | `/books/<book_id>/` | Chi tiết sách / thêm vào giỏ (customer) + ghi nhận hành vi |
| GET | `/books/<book_id>/delete/` | Xóa sách (staff) |
| GET | `/customers/` | Danh sách khách hàng |
| GET/POST | `/cart/<customer_id>/` | Xem giỏ hàng / thêm sản phẩm |
| GET/POST | `/cart/<customer_id>/checkout/` | Xác nhận đơn từ giỏ → tạo đơn → redirect thanh toán |
| GET | `/orders/` | Danh sách đơn hàng |
| GET/POST | `/orders/<order_id>/pay/` | Thanh toán đơn (chọn phương thức, xác nhận) |
| GET | `/orders/customer/<customer_id>/` | Đơn hàng theo khách |
| GET | `/catalog/` | Catalog (danh mục) |

---

## 2. Customer Service `:8001` (Identity)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| POST | `/auth/login/` | Đăng nhập → `{user, access, refresh}` | — |
| POST | `/auth/register/` | Đăng ký → tạo customer + cart | — |
| POST | `/auth/refresh/` | Refresh access token | — |
| GET | `/auth/me/` | Thông tin user hiện tại | Bearer |
| GET | `/customers/` | Danh sách customer | Staff/Manager |
| POST | `/customers/` | Tạo customer | Staff/Manager |
| GET | `/customers/<pk>/` | Chi tiết customer | Auth |
| PUT | `/customers/<pk>/` | Cập nhật customer | Auth |
| DELETE | `/customers/<pk>/` | Xóa customer | Staff/Manager |
| GET | `/customers/<id>/addresses/` | Danh sách địa chỉ | Auth |
| POST | `/customers/<id>/addresses/` | Thêm địa chỉ | Auth |
| PUT/DELETE | `/customers/<id>/addresses/<pk>/` | Sửa/xóa địa chỉ | Auth |

---

## 3. Staff Service `:8004` (Identity)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| POST | `/auth/login/` | Đăng nhập staff | — |
| POST | `/auth/refresh/` | Refresh token | — |
| GET | `/auth/me/` | Thông tin staff | Bearer |
| GET | `/staff/` | Danh sách staff | Manager |
| POST | `/staff/` | Tạo staff | Manager |
| GET/PUT/DELETE | `/staff/<pk>/` | Chi tiết / sửa / xóa staff | Manager |

---

## 4. Manager Service `:8005` (Inventory)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/warehouses/` | Danh sách kho | Manager |
| POST | `/warehouses/` | Tạo kho | Manager |
| GET/PUT/DELETE | `/warehouses/<pk>/` | Chi tiết / sửa / xóa kho | Manager |
| GET | `/inventory/` | Tồn kho | Manager |
| POST | `/inventory/` | Tạo/cập nhật tồn kho | Manager |
| GET | `/suppliers/` | Danh sách nhà cung cấp | Manager |
| POST | `/suppliers/` | Tạo supplier | Manager |
| GET/PUT/DELETE | `/suppliers/<pk>/` | Chi tiết / sửa / xóa supplier | Manager |
| GET | `/purchase-orders/` | Đơn mua hàng | Manager |
| POST | `/purchase-orders/` | Tạo đơn mua | Manager |
| GET/PUT/DELETE | `/purchase-orders/<pk>/` | Chi tiết / sửa / xóa PO | Manager |

---

## 5. Book Service `:8002` (Catalog)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/books/` | Danh sách sách (`?search=`, `?status=`) | — |
| POST | `/books/` | Tạo sách | Staff |
| GET | `/books/<pk>/` | Chi tiết sách | — |
| PUT | `/books/<pk>/` | Cập nhật sách | Staff |
| DELETE | `/books/<pk>/` | Xóa sách | Staff |

---

## 6. Catalog Service `:8006` (Category, Author, Publisher)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET/POST | `/authors/` | Danh sách / tạo tác giả | — / Staff |
| GET/PUT/DELETE | `/authors/<pk>/` | Chi tiết / sửa / xóa | Staff |
| GET/POST | `/categories/` | Danh sách / tạo category | — / Staff |
| GET/PUT/DELETE | `/categories/<pk>/` | Chi tiết / sửa / xóa | Staff |
| GET/POST | `/genres/` | Danh sách / tạo genre | — / Staff |
| GET/PUT/DELETE | `/genres/<pk>/` | Chi tiết / sửa / xóa | Staff |
| GET/POST | `/publishers/` | Danh sách / tạo NXB | — / Staff |
| GET/PUT/DELETE | `/publishers/<pk>/` | Chi tiết / sửa / xóa | Staff |

---

## 7. Cart Service `:8003` (Ordering)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| POST | `/carts/` | Tạo cart (internal: `customer_id` trong body) | Internal |
| GET | `/carts/<customer_id>/` | Xem giỏ hàng | Customer (chỉ cart của mình) |
| DELETE | `/carts/<customer_id>/` | Xóa giỏ hàng | Customer |
| GET | `/carts/<customer_id>/items/` | Danh sách item trong giỏ | Auth |
| POST | `/carts/<customer_id>/items/` | Thêm item (`book_id`, `quantity`) | Auth |
| PUT/DELETE | `/carts/<customer_id>/items/<item_id>/` | Sửa / xóa item | Auth |

---

## 8. Order Service `:8007` (Ordering)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/orders/` | Danh sách đơn (`?customer_id=` cho staff) | Customer/Staff |
| POST | `/orders/` | Tạo đơn (body: `customer_id`, `items[]`, `discount_code`, `shipping_fee`) | Customer |
| GET | `/orders/<pk>/` | Chi tiết đơn | Auth |
| PUT | `/orders/<pk>/` | Cập nhật trạng thái (`status`) | Staff |
| DELETE | `/orders/<pk>/` | Hủy đơn | Customer |
| GET/POST | `/discounts/` | Danh sách / tạo mã giảm giá | Staff |

---

## 9. Pay Service `:8008` (Fulfillment)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/payment-methods/` | Danh sách phương thức thanh toán | — |
| GET | `/payments/` | Danh sách thanh toán | Auth |
| POST | `/payments/` | Tạo thanh toán (gắn với order) | Auth |
| GET | `/payments/<pk>/` | Chi tiết thanh toán | Auth |
| POST | `/payments/<payment_id>/refund/` | Hoàn tiền | Staff |

---

## 10. Ship Service `:8009` (Fulfillment)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/shipping-methods/` | Danh sách phương thức giao hàng | — |
| GET | `/shippings/` | Danh sách đơn giao | Auth |
| POST | `/shippings/` | Tạo đơn giao (gắn order) | Auth |
| GET | `/shippings/<pk>/` | Chi tiết đơn giao | Auth |

---

## 11. Comment-Rate Service `:8010` (Review)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/reviews/` | Danh sách review (`?book_id=`, `?customer_id=`) | — |
| POST | `/reviews/` | Tạo review (rating 1–5, nội dung) | Auth |
| GET | `/reviews/<pk>/` | Chi tiết review | — |
| PUT | `/reviews/<pk>/` | Sửa review | Author |
| DELETE | `/reviews/<pk>/` | Xóa review | Author |
| GET | `/books/<book_id>/rating/` | Điểm trung bình theo sách | — |

---

## 12. Recommender AI Service `:8011` (Recommendation)

| Method | Path | Mô tả | Auth |
|--------|------|--------|------|
| GET | `/recommendations/<customer_id>/` | Gợi ý sách theo khách hàng | Auth |
| POST | `/api/recommender/events/` | Ghi nhận hành vi người dùng (`click`, `view`, `cart_add`, ...) | Auth |

---

## Giao tiếp nội bộ (service → service)

- **customer-service** → **cart-service**: `POST /carts/` (khi đăng ký customer).
- **cart-service** → **book-service**: `GET /books/<id>/` (validate book_id, lấy giá).
- **order-service** → **book-service**: `GET /books/<id>/` (lấy giá khi tạo đơn).
- **order-service** → **pay-service**: `POST /payments/`.
- **order-service** → **ship-service**: `POST /shippings/`.
- **order-service** → **comment-rate-service**: `GET /reviews/` (nếu dùng khi tạo đơn).
- **recommender-ai-service** → **book-service**: `GET /books/`; → **order-service**: `GET /orders/`.

---

## Auth header (backend services)

```
Authorization: Bearer <access_token>
```

Gateway có thể truyền thêm header (ví dụ `X-User-Id`, `X-Role`, `X-Entity-Id`) sau khi verify JWT để backend biết user/role.
