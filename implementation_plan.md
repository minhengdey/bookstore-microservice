# Lên Kế Hoạch Nâng Cấp Hệ Thống E-commerce Hiện Đại

Bản thiết kế mới mà bạn đề xuất đòi hỏi việc mở rộng kiến trúc vi dịch vụ (microservices) hiện tại, cập nhật Frontend (API Gateway / Templates), và thay đổi schema database của nhiều service.

Vì khối lượng công việc rất lớn (tương đương việc xây dựng một hệ thống E-commerce thực tế hoàn chỉnh), tôi đề xuất chia nhỏ quá trình phát triển thành **4 Giai đoạn (Phases)**. Chúng ta sẽ thực hiện cuốn chiếu từng giai đoạn.

## User Review Required

> [!IMPORTANT]
> Việc xây dựng toàn bộ kiến trúc này sẽ mất nhiều thời gian. Vui lòng xem xét các lộ trình dưới đây và cho biết bạn có đồng ý thực hiện **Giai đoạn 1** trước không, hay có thay đổi mức độ ưu tiên nào?

## Giai đoạn 1: Trải nghiệm Mua sắm Nâng cao (Public & Shopping Core)

Tập trung nâng cấp trải nghiệm tìm kiếm, xem sản phẩm và khuyến mãi.

### Frontend / API Gateway (`api-gateway`)

- **[MODIFY]** `gateway/urls.py` & `gateway/views.py`: Thêm các route cho Khuyến mãi (`/promotions`), cập nhật route Tìm kiếm sản phẩm (`/products`) để hỗ trợ bộ lọc phức tạp.
- **[MODIFY]** `templates/home.html`: Thêm khu vực Banner, Flash Sale, Sản phẩm bán chạy.
- **[MODIFY]** `templates/product_detail.html`: Thêm phần Đánh giá khách hàng, Video sản phẩm (nếu có URL), và cấu hình biến thể (màu sắc, kích thước).

### Backend Services

- **[NEW]** `promotion-service`: Một service hoàn toàn mới để quản lý Voucher, Flash Sale, Coupon. (Bao gồm cấu hình Docker, Database PostgreSQL mới).
- **[MODIFY]** `product-service`: Bổ sung model `ProductVariant` (Biến thể sản phẩm) và các API lọc/sắp xếp nâng cao (giá tăng/giảm, bán chạy, đánh giá sao).
- **[MODIFY]** `interaction-service`: Mở rộng API đánh giá (Review) cho phép tải lên hình ảnh và bình luận text.

---

## Giai đoạn 2: Tối ưu Trải nghiệm Khách hàng (Customer Journey)

Tập trung vào cá nhân hóa, thanh toán và theo dõi đơn hàng.

### Frontend / API Gateway (`api-gateway`)

- **[NEW]** Màn hình Quản lý hồ sơ (`/profile`), Địa chỉ (`/addresses`), Wishlist (`/wishlist`).
- **[MODIFY]** `templates/checkout.html`: Tích hợp phần chọn Đơn vị vận chuyển, áp dụng Voucher, tính Phí ship động.
- **[NEW]** Màn hình Theo dõi vận chuyển (`/tracking/{id}`) và Trả hàng (`/returns`).

### Backend Services

- **[MODIFY]** `user-service`: Hỗ trợ CRUD cho danh sách địa chỉ giao hàng (`UserAddress`).
- **[MODIFY]** `cart-service` & `order-service`: Tích hợp gọi giao tiếp với `promotion-service` để xác thực và áp dụng mã giảm giá.
- **[MODIFY]** `shipping-service`: Xây dựng logic tính phí ship dựa trên khoảng cách/khối lượng và thiết kế API Tracking trạng thái đơn hàng.
- **[MODIFY]** `payment-service`: Bổ sung mock flow cho các cổng thanh toán online (VNPay, MoMo, ZaloPay).

---

## Giai đoạn 3: Vận hành & Chăm sóc Khách hàng (Staff Operations)

Cung cấp công cụ cho đội ngũ vận hành.

### Frontend / API Gateway (`api-gateway`)

- **[NEW]** Xây dựng cụm giao diện `/staff/*` bao gồm Dashboard thống kê, Quản lý đơn hàng (Duyệt/Hủy), và xem lịch sử của Khách hàng.
- **[NEW]** Giao diện Hỗ trợ khách hàng (Ticket/Chat).

### Backend Services

- **[MODIFY]** `order-service`: Bổ sung API cho Staff duyệt đơn hàng loạt.
- **[NEW]** `support-service` (hoặc mở rộng `interaction-service`): Lưu trữ Ticket khiếu nại và lịch sử Chat giữa Staff và Customer.

---

## Giai đoạn 4: Quản trị Cấp cao & AI (Manager/Admin)

Xây dựng hệ thống báo cáo, cấu hình AI và kiểm soát toàn diện.

### Frontend / API Gateway (`api-gateway`)

- **[NEW]** Giao diện `/admin/*`: Dashboard doanh thu chi tiết, CRUD toàn bộ thực thể (Product, Category, Brand, User, Inventory).
- **[NEW]** Giao diện Báo cáo & Thống kê (`/admin/reports`).
- **[NEW]** Giao diện Quản lý AI Recommendation (`/admin/recommendation`).

### Backend Services

- Xây dựng hệ thống Role-based access control (RBAC) chặt chẽ trên TẤT CẢ các admin APIs.
- **[MODIFY]** `recommender-ai-service`: Bổ sung API trigger retraining model thủ công, dashboard theo dõi metrics (Accuracy, F1), quản lý Model versioning.

## Verification Plan

1. **Automated Verification**: Kiểm tra Docker Compose khởi chạy thành công `promotion-service` (Giai đoạn 1). Gọi test endpoint để đảm bảo API hoạt động.
2. **Manual Verification**: Sau mỗi giai đoạn, người dùng sẽ kiểm thử trực tiếp trên trình duyệt giao diện mới (ví dụ: Trang chủ mới, bộ lọc Sản phẩm) trước khi chuyển qua phase tiếp theo.