# Danh sách Màn hình và Phân quyền Hệ thống E-Commerce

## 1. Nhóm Chức năng Công khai (Public)

### 1.1 Trang chủ (Home)

**URL:** `/`

**Nội dung:**

* Banner quảng cáo.
* Flash Sale.
* Danh mục nổi bật.
* Sản phẩm mới.
* Sản phẩm bán chạy.
* Sản phẩm giảm giá.
* Sản phẩm gợi ý AI.
* Thống kê tổng quan.

**Quyền truy cập:** Public.

---

### 1.2 Đăng nhập

**URL:** `/login`

**Nội dung:**

* Email/SĐT.
* Mật khẩu.
* Đăng nhập Google.
* Đăng nhập Facebook.
* Quên mật khẩu.

**Quyền:** Public.

---

### 1.3 Đăng ký

**URL:** `/register`

**Nội dung:**

* Họ tên.
* Email.
* SĐT.
* Mật khẩu.
* Xác thực OTP Email/SMS.

**Quyền:** Public.

---

### 1.4 Quên mật khẩu

**URL:** `/forgot-password`

**Nội dung:**

* Nhập Email.
* Gửi OTP.
* Đặt lại mật khẩu.

**Quyền:** Public.

---

### 1.5 Danh sách sản phẩm

**URL:** `/products`

**Nội dung:**

* Phân trang.
* Tìm kiếm.
* Lọc theo:

  * Danh mục.
  * Thương hiệu.
  * Giá.
  * Đánh giá.
  * Tình trạng kho.
* Sắp xếp:

  * Mới nhất.
  * Giá tăng.
  * Giá giảm.
  * Bán chạy.

**Quyền:** Public.

---

### 1.6 Chi tiết sản phẩm

**URL:** `/products/{id}`

**Nội dung:**

* Hình ảnh sản phẩm.
* Video sản phẩm.
* Thông tin chi tiết.
* Giá gốc.
* Giá khuyến mãi.
* Tồn kho.
* Thuộc tính sản phẩm.
* Đánh giá khách hàng.
* Sản phẩm liên quan.
* AI Recommendation.

**Quyền:** Public.

---

### 1.7 Danh mục sản phẩm

**URL:** `/categories`

**Nội dung:**

* Danh sách danh mục.
* Danh mục con.

**Quyền:** Public.

---

### 1.8 Trang khuyến mãi

**URL:** `/promotions`

**Nội dung:**

* Voucher.
* Flash Sale.
* Combo giảm giá.

**Quyền:** Public.

---

# 2. Nhóm Chức năng Khách hàng (Customer)

## 2.1 Hồ sơ cá nhân

**URL:** `/profile`

**Nội dung:**

* Thông tin cá nhân.
* Avatar.
* Đổi mật khẩu.

**Quyền:** Customer.

---

## 2.2 Quản lý địa chỉ giao hàng

**URL:** `/addresses`

**Nội dung:**

* Thêm địa chỉ.
* Sửa địa chỉ.
* Xóa địa chỉ.
* Chọn mặc định.

**Quyền:** Customer.

---

## 2.3 Danh sách yêu thích

**URL:** `/wishlist`

**Nội dung:**

* Các sản phẩm yêu thích.

**Quyền:** Customer.

---

## 2.4 Giỏ hàng

**URL:** `/cart`

**Nội dung:**

* Danh sách sản phẩm.
* Số lượng.
* Tổng tiền.
* Voucher áp dụng.

**Quyền:** Customer.

---

## 2.5 Thanh toán (Checkout)

**URL:** `/checkout`

**Nội dung:**

* Chọn địa chỉ.
* Chọn đơn vị vận chuyển.
* Chọn phương thức thanh toán.
* Áp dụng voucher.
* Tính phí ship.

**Quyền:** Customer.

---

## 2.6 Thanh toán Online

**URL:** `/payment`

**Hỗ trợ:**

* COD.
* VNPay.
* MoMo.
* ZaloPay.
* Banking.

**Quyền:** Customer.

---

## 2.7 Lịch sử đơn hàng

**URL:** `/orders`

**Nội dung:**

* Chờ xác nhận.
* Đang xử lý.
* Đang giao.
* Đã giao.
* Đã hủy.
* Hoàn trả.

**Quyền:** Customer.

---

## 2.8 Chi tiết đơn hàng

**URL:** `/orders/{id}`

**Nội dung:**

* Chi tiết sản phẩm.
* Trạng thái đơn.
* Timeline xử lý.

**Quyền:** Customer.

---

## 2.9 Theo dõi vận chuyển

**URL:** `/tracking/{orderId}`

**Nội dung:**

* Trạng thái vận chuyển realtime.
* Vị trí đơn hàng.

**Quyền:** Customer.

---

## 2.10 Đánh giá sản phẩm

**URL:** `/reviews`

**Nội dung:**

* Đánh giá sao.
* Bình luận.
* Hình ảnh.

**Quyền:** Customer đã mua hàng.

---

## 2.11 Khiếu nại / Hoàn trả

**URL:** `/returns`

**Nội dung:**

* Yêu cầu đổi trả.
* Upload hình ảnh minh chứng.

**Quyền:** Customer.

---

## 2.12 Gợi ý sản phẩm AI

**URL:** `/recommendations`

**Nội dung:**

* Personalized Recommendation.
* Similar Products.
* Frequently Bought Together.

**Quyền:** Customer.

---

# 3. Nhóm Chức năng Nhân viên (Staff)

## 3.1 Dashboard

**URL:** `/staff/dashboard`

**Nội dung:**

* Đơn hàng hôm nay.
* Doanh thu hôm nay.
* Khách hàng mới.

**Quyền:** Staff.

---

## 3.2 Quản lý đơn hàng

**URL:** `/staff/orders`

**Nội dung:**

* Duyệt đơn.
* Cập nhật trạng thái.
* Hủy đơn.

**Quyền:** Staff.

---

## 3.3 Quản lý khách hàng

**URL:** `/staff/customers`

**Nội dung:**

* Xem thông tin khách hàng.
* Xem lịch sử mua hàng.

**Quyền:** Staff.

---

## 3.4 Hỗ trợ khách hàng

**URL:** `/staff/support`

**Nội dung:**

* Ticket hỗ trợ.
* Chat với khách hàng.

**Quyền:** Staff.

---

# 4. Nhóm Chức năng Quản lý (Manager/Admin)

## 4.1 Dashboard quản trị

**URL:** `/admin/dashboard`

**Nội dung:**

* Doanh thu.
* Lợi nhuận.
* Sản phẩm bán chạy.
* Top khách hàng.
* Biểu đồ thống kê.

**Quyền:** Manager/Admin.

---

## 4.2 Quản lý sản phẩm

**URL:** `/admin/products`

**Nội dung:**

* CRUD sản phẩm.
* Quản lý tồn kho.
* Quản lý biến thể.

**Quyền:** Manager/Admin.

---

## 4.3 Quản lý danh mục

**URL:** `/admin/categories`

**Nội dung:**

* CRUD danh mục.

**Quyền:** Manager/Admin.

---

## 4.4 Quản lý thương hiệu

**URL:** `/admin/brands`

**Nội dung:**

* CRUD thương hiệu.

**Quyền:** Manager/Admin.

---

## 4.5 Quản lý kho hàng

**URL:** `/admin/inventory`

**Nội dung:**

* Nhập kho.
* Xuất kho.
* Kiểm kê.

**Quyền:** Manager/Admin.

---

## 4.6 Quản lý khuyến mãi

**URL:** `/admin/promotions`

**Nội dung:**

* Voucher.
* Coupon.
* Flash Sale.

**Quyền:** Manager/Admin.

---

## 4.7 Quản lý đơn hàng

**URL:** `/admin/orders`

**Nội dung:**

* Toàn bộ đơn hàng.
* Hoàn tiền.
* Đổi trả.

**Quyền:** Manager/Admin.

---

## 4.8 Quản lý người dùng

**URL:** `/admin/users`

**Nội dung:**

* CRUD User.
* Khóa tài khoản.
* Phân quyền.

**Quyền:** Manager/Admin.

---

## 4.9 Quản lý đánh giá

**URL:** `/admin/reviews`

**Nội dung:**

* Duyệt đánh giá.
* Ẩn bình luận vi phạm.

**Quyền:** Manager/Admin.

---

## 4.10 Báo cáo & Thống kê

**URL:** `/admin/reports`

**Nội dung:**

* Doanh thu theo ngày/tháng/năm.
* Sản phẩm bán chạy.
* Hiệu quả khuyến mãi.
* Tỷ lệ chuyển đổi.
* Hành vi khách hàng.

**Quyền:** Manager/Admin.

---

## 4.11 Quản lý AI Recommendation

**URL:** `/admin/recommendation`

**Nội dung:**

* Theo dõi dữ liệu hành vi.
* Chạy train model.
* Đánh giá Accuracy/F1.
* Quản lý Dataset.
* Quản lý Model Version.
* Theo dõi API Recommender.

**Quyền:** Manager/Admin.

---

# Phân quyền tổng quát

| Chức năng          | Public | Customer     | Staff | Manager/Admin |
| ------------------ | ------ | ------------ | ----- | ------------- |
| Xem sản phẩm       | ✅      | ✅            | ✅     | ✅             |
| Mua hàng           | ❌      | ✅            | ❌     | ❌             |
| Giỏ hàng           | ❌      | ✅            | ❌     | ❌             |
| Wishlist           | ❌      | ✅            | ❌     | ❌             |
| Đánh giá sản phẩm  | ❌      | ✅            | ❌     | ❌             |
| Quản lý đơn hàng   | ❌      | Xem của mình | ✅     | ✅             |
| Quản lý sản phẩm   | ❌      | ❌            | ❌     | ✅             |
| Quản lý kho        | ❌      | ❌            | ❌     | ✅             |
| Quản lý người dùng | ❌      | ❌            | ❌     | ✅             |
| Quản lý khuyến mãi | ❌      | ❌            | ❌     | ✅             |
| Dashboard thống kê | ❌      | ❌            | ✅     | ✅             |
| AI Recommendation  | ❌      | Xem gợi ý    | ❌     | ✅             |
