# Requirements Document

## Introduction

Tài liệu này mô tả các yêu cầu cho 4 nhiệm vụ cải tiến hệ thống thương mại điện tử microservices dựa trên Django. Các cải tiến bao gồm: sửa lỗi seed script dùng giá trị cứng, commit các thay đổi chưa được lưu liên quan đến Saga/Outbox, thêm consumer cho Dead Letter Queue (DLQ), và tạo script kiểm thử end-to-end tự động.

## Glossary

- **Seed_Script**: Tệp SQL dùng để chèn dữ liệu mẫu vào cơ sở dữ liệu khi khởi tạo môi trường phát triển.
- **Sequence**: Bộ đếm tự tăng của PostgreSQL dùng để sinh giá trị `id` cho bảng.
- **setval**: Hàm PostgreSQL dùng để đặt lại giá trị hiện tại của một sequence.
- **COALESCE**: Hàm SQL trả về giá trị đầu tiên không NULL trong danh sách tham số.
- **Outbox_Pattern**: Mẫu thiết kế đảm bảo tính nhất quán giữa cập nhật cơ sở dữ liệu và xuất bản sự kiện bằng cách ghi sự kiện vào bảng outbox trong cùng một transaction.
- **Saga**: Mẫu quản lý giao dịch phân tán qua chuỗi các bước cục bộ có thể bù trừ.
- **DLQ**: Dead Letter Queue – hàng đợi chứa các message không thể xử lý thành công sau nhiều lần thử.
- **DLX**: Dead Letter Exchange – exchange RabbitMQ định tuyến message thất bại vào DLQ.
- **DLQEvent**: Model Django lưu trữ thông tin các message bị đưa vào DLQ để theo dõi và phát lại.
- **Payment_Consumer**: Tiến trình Django management command tiêu thụ sự kiện từ `order_events` exchange.
- **E2E_Test_Script**: Script Python độc lập kiểm thử luồng hoàn chỉnh từ đăng ký người dùng đến thanh toán và giao hàng.
- **JWT**: JSON Web Token – cơ chế xác thực stateless được dùng trong hệ thống.
- **API_Gateway**: Dịch vụ Django BFF (Backend For Frontend) đóng vai trò cổng vào duy nhất cho client.
- **OrderOutbox**: Bảng outbox trong `order-service` lưu sự kiện `order_created` chờ relay sang RabbitMQ.
- **PaymentOutbox**: Bảng outbox trong `payment-service` lưu sự kiện `payment_completed` chờ relay sang RabbitMQ.

---

## Requirements

### Yêu cầu 1: Sửa Seed Script – Dùng setval động

**User Story:** Là một developer, tôi muốn các seed script SQL sử dụng `setval` động thay vì giá trị cứng, để tránh xung đột `id` khi seed được chạy nhiều lần hoặc khi bảng đã có dữ liệu.

#### Tiêu chí chấp nhận

1. THE Seed_Script SHALL thay thế tất cả lệnh `SELECT setval(pg_get_serial_sequence('table','id'), N)` có giá trị `N` cứng bằng `SELECT setval(pg_get_serial_sequence('table','id'), COALESCE((SELECT MAX(id) FROM table), 1))`.
2. WHEN `13_user_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `users`, `customer_profiles`, `staff_profiles`, `web_addresses`.
3. WHEN `06_order_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `discounts`, `orders`, `order_items`, `order_discounts`, `invoices`, `coupons`.
4. WHEN `07_pay_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `payment_methods`, `payments`, `transactions`, `customer_payment_methods`.
5. WHEN `08_ship_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `shipping_methods`, `shippings`.
6. WHEN `12_product_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `categories`, `products`.
7. WHEN `02_catalog_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `authors`, `categories`, `genres`, `publishers`.
8. WHEN `03_book_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho bảng: `books`.
9. WHEN `04_staff_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `staff_users`, `inventory_staff`.
10. WHEN `05_cart_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `carts`, `cart_items`.
11. WHEN `09_manager_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho các bảng: `warehouses`, `suppliers`, `purchase_orders`.
12. WHEN `10_comment_rate_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho bảng: `book_reviews`.
13. WHEN `11_recommender_db_seed.sql` được chạy, THE Seed_Script SHALL cập nhật sequence động cho bảng: `recommendation_logs`.
14. IF bảng đang rỗng (không có dữ liệu), THEN THE Seed_Script SHALL đặt sequence về giá trị `1` thay vì `NULL` để tránh lỗi.
15. WHEN `seed_all.sh` được chạy, THE Seed_Script SHALL xác minh rằng sequence của bảng `auth_users` trong `auth_db` được cập nhật động sau khi seed.

---

### Yêu cầu 2: Git Commit – Lưu các thay đổi Saga/Outbox

**User Story:** Là một developer, tôi muốn commit tất cả các thay đổi chưa được lưu liên quan đến việc triển khai Saga Orchestration với Outbox Pattern, để lịch sử git phản ánh đúng trạng thái hiện tại của hệ thống.

#### Tiêu chí chấp nhận

1. WHEN lệnh git commit được thực thi, THE Git_Repository SHALL tạo một commit mới với message chính xác là `feat: implement saga orchestration with outbox pattern`.
2. THE Git_Repository SHALL bao gồm trong commit các tệp sau:
   - `docker-compose.yml`
   - `api-gateway/gateway/views.py`
   - `api-gateway/templates/` (toàn bộ thư mục)
   - `common/common/client.py`
   - `order-service/entrypoint.sh`
   - `order-service/order/models.py`
   - `order-service/requirements.txt`
   - `order-service/order/migrations/0002_orderoutbox.py`
   - `order-service/order/migrations/0003_orderoutbox_index.py`
   - `payment-service/payment/management/commands/consume_orders.py`
   - `payment-service/requirements.txt`
   - `product-service/product/models.py`
   - `product-service/requirements.txt`
   - `product-service/product/migrations/0003_product_image_url.py`
   - `recommender-ai-service/app/management/commands/seed_mock.py`
   - `scripts/init_databases.sql`
   - `scripts/sql/06_order_db_seed.sql`
   - `scripts/sql/12_product_db_seed.sql`
   - `scripts/sql/13_user_db_seed.sql`
   - `api-gateway/static/product-images/` (toàn bộ thư mục)
3. THE Git_Repository SHALL chỉ stage các tệp được liệt kê ở tiêu chí 2, không stage các tệp không liên quan.
4. IF một tệp trong danh sách không tồn tại hoặc không có thay đổi, THEN THE Git_Repository SHALL bỏ qua tệp đó và tiếp tục stage các tệp còn lại.

---

### Yêu cầu 3: Thêm DLQ Consumer

**User Story:** Là một system operator, tôi muốn có một consumer theo dõi Dead Letter Queue, để tôi có thể nhìn thấy và phát lại các message thất bại trong luồng xử lý thanh toán.

#### Tiêu chí chấp nhận

1. THE DLQ_Consumer SHALL là một Django management command tại `payment-service/payment/management/commands/consume_dlq.py` tiêu thụ message từ hàng đợi `dlq`.
2. WHEN một message được nhận từ `dlq`, THE DLQ_Consumer SHALL ghi log đầy đủ thông tin bao gồm: `event_type`, `order_id`, `error` (nếu có), và `timestamp`.
3. WHEN một message được nhận từ `dlq`, THE DLQ_Consumer SHALL lưu thông tin message vào model `DLQEvent` trong cơ sở dữ liệu `pay_db`.
4. THE DLQEvent_Model SHALL có các trường: `id` (auto), `queue_name` (CharField), `exchange` (CharField), `routing_key` (CharField), `body` (JSONField), `error_message` (TextField), `received_at` (DateTimeField, auto_now_add=True), `replayed` (BooleanField, default=False).
5. THE DLQEvent_Model SHALL được lưu trong bảng `dlq_events` của cơ sở dữ liệu `pay_db`.
6. WHEN migration được tạo cho `DLQEvent`, THE Migration SHALL được đặt tại `payment-service/payment/migrations/` với tên phù hợp theo quy ước Django.
7. WHEN `docker-compose.yml` được cập nhật, THE Docker_Compose SHALL thêm service `dlq-consumer` với cấu hình: build từ `payment-service`, chạy lệnh `python manage.py consume_dlq`, phụ thuộc vào `rabbitmq` và `payment-db`.
8. WHEN `dlq-consumer` service khởi động, THE DLQ_Consumer SHALL kết nối đến RabbitMQ và bắt đầu tiêu thụ từ hàng đợi `dlq` đã được khai báo sẵn trong `common/common/events.py`.
9. IF một message trong `dlq` không thể parse thành JSON hợp lệ, THEN THE DLQ_Consumer SHALL vẫn lưu nội dung thô vào trường `body` và ghi log cảnh báo.
10. WHEN một message được xử lý thành công bởi DLQ_Consumer, THE DLQ_Consumer SHALL gửi `basic_ack` để xác nhận message đã được tiêu thụ.

---

### Yêu cầu 4: Script Kiểm thử End-to-End Tự động

**User Story:** Là một developer hoặc QA engineer, tôi muốn có một script kiểm thử end-to-end tự động, để tôi có thể xác minh toàn bộ luồng từ đăng ký người dùng đến thanh toán và giao hàng hoạt động đúng.

#### Tiêu chí chấp nhận

1. THE E2E_Test_Script SHALL được tạo tại `scripts/e2e_test.py` và chỉ sử dụng thư viện chuẩn Python (`stdlib`) cùng thư viện `requests`.
2. THE E2E_Test_Script SHALL đọc URL cơ sở từ biến môi trường `BASE_URL` với giá trị mặc định là `http://localhost:8000`.
3. WHEN script được chạy, THE E2E_Test_Script SHALL thực hiện tuần tự các bước sau:
   - Bước 1: Đăng ký người dùng mới (POST `/auth/register/`) với `username` và `email` ngẫu nhiên.
   - Bước 2: Đăng nhập (POST `/auth/login/`) và lấy JWT access token.
   - Bước 3: Lấy danh sách sản phẩm (GET `/products/`) và chọn sản phẩm đầu tiên.
   - Bước 4: Thêm sản phẩm vào giỏ hàng (POST `/carts/{customer_id}/items/`).
   - Bước 5: Tạo đơn hàng (POST `/orders/`) và lấy `order_id`.
   - Bước 6: Thanh toán (POST `/payments/`) với `payment_method_id=1`.
   - Bước 7: Kiểm tra trạng thái thanh toán (GET `/payments/?order_id={id}`) – thử lại tối đa 10 lần, mỗi lần cách nhau 2 giây.
   - Bước 8: Kiểm tra trạng thái giao hàng (GET `/shippings/?order_id={id}`) – thử lại tối đa 10 lần, mỗi lần cách nhau 2 giây.
4. WHEN mỗi bước hoàn thành, THE E2E_Test_Script SHALL in kết quả PASS (màu xanh lá) hoặc FAIL (màu đỏ) kèm thời gian thực thi của bước đó sử dụng mã ANSI.
5. WHEN toàn bộ script hoàn thành thành công, THE E2E_Test_Script SHALL thoát với mã `0`.
6. IF bất kỳ bước nào thất bại, THEN THE E2E_Test_Script SHALL thoát với mã `1`.
7. WHEN script được chạy với flag `--dry-run`, THE E2E_Test_Script SHALL bỏ qua tất cả các lệnh gọi HTTP thực tế và chỉ in kế hoạch thực thi các bước.
8. WHEN bước poll trạng thái thanh toán hoặc giao hàng đạt tối đa 10 lần thử mà chưa nhận được trạng thái thành công, THEN THE E2E_Test_Script SHALL đánh dấu bước đó là FAIL và dừng script.
9. THE E2E_Test_Script SHALL in báo cáo tổng kết cuối cùng liệt kê kết quả PASS/FAIL và thời gian của từng bước.
