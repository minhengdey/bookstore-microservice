# Implementation Plan: saga-improvements

## Tasks

- [x] 1. Sửa Seed Script – Thay thế setval cứng bằng COALESCE động
  Mở từng file SQL trong `scripts/sql/` và thay thế tất cả lệnh `SELECT setval(pg_get_serial_sequence('table','id'), N)` (N là số cứng) bằng `SELECT setval(pg_get_serial_sequence('table','id'), COALESCE((SELECT MAX(id) FROM table), 1))`. Các file cần sửa: `13_user_db_seed.sql`, `06_order_db_seed.sql`, `07_pay_db_seed.sql`, `08_ship_db_seed.sql`, `12_product_db_seed.sql`, `02_catalog_db_seed.sql`, `03_product_db_seed.sql`, `04_staff_db_seed.sql`, `05_cart_db_seed.sql`, `09_manager_db_seed.sql`, `10_comment_rate_db_seed.sql`, `11_recommender_db_seed.sql`. Xác minh `seed_all.sh` đã có case `auth-service` với pattern COALESCE cho `auth_users`.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13, 1.14, 1.15

- [x] 2. Git Commit – Stage và commit các thay đổi Saga/Outbox
  Chạy `git add` cho từng file/thư mục: `docker-compose.yml`, `api-gateway/gateway/views.py`, `api-gateway/templates/`, `common/common/client.py`, `order-service/entrypoint.sh`, `order-service/order/models.py`, `order-service/requirements.txt`, `order-service/order/migrations/0002_orderoutbox.py`, `order-service/order/migrations/0003_orderoutbox_index.py`, `payment-service/payment/management/commands/consume_orders.py`, `payment-service/requirements.txt`, `product-service/product/models.py`, `product-service/requirements.txt`, `product-service/product/migrations/0003_product_image_url.py`, `recommender-ai-service/app/management/commands/seed_mock.py`, `scripts/init_databases.sql`, `scripts/sql/06_order_db_seed.sql`, `scripts/sql/12_product_db_seed.sql`, `scripts/sql/13_user_db_seed.sql`, `api-gateway/static/product-images/`. Sau đó chạy `git commit -m "feat: implement saga orchestration with outbox pattern"`. Bỏ qua nếu file không tồn tại hoặc không có thay đổi.
  - Requirements: 2.1, 2.2, 2.3, 2.4
  - Depends on: 1

- [x] 3. Tạo model DLQEvent và migration
  Thêm class `DLQEvent` vào cuối `payment-service/payment/models.py` với các trường: `queue_name` (CharField max_length=255), `exchange` (CharField max_length=255, blank=True), `routing_key` (CharField max_length=255, blank=True), `body` (JSONField), `error_message` (TextField, blank=True), `received_at` (DateTimeField, auto_now_add=True), `replayed` (BooleanField, default=False). Đặt `db_table = "dlq_events"` trong Meta. Sau đó tạo thủ công file migration Django tại `payment-service/payment/migrations/` để tạo bảng `dlq_events`.
  - Requirements: 3.4, 3.5, 3.6

- [x] 4. Tạo management command consume_dlq.py
  Tạo `payment-service/payment/management/commands/consume_dlq.py` với class `Command(BaseCommand)`. Trong `handle`: lấy channel từ `EventPublisher.get_channel()`, khai báo lại `dlq` queue (idempotent), đăng ký callback `on_dlq_message`, gọi `channel.start_consuming()`. Trong callback: decode bytes → string, parse JSON (bắt `JSONDecodeError` → `{"_raw": raw}`), trích xuất `event_type` và `order_id`, ghi log `logger.error(...)`, tạo `DLQEvent` trong DB, gọi `ch.basic_ack(delivery_tag=method.delivery_tag)`. Xử lý `KeyboardInterrupt` gracefully.
  - Requirements: 3.1, 3.2, 3.3, 3.8, 3.9, 3.10
  - Depends on: 3

- [x] 5. Thêm service dlq-consumer vào docker-compose.yml
  Mở `docker-compose.yml` và thêm service `dlq-consumer` vào section `# ── Workers & Consumers` (sau `payment-outbox-worker`). Cấu hình: `build: ./payment-service`, `command: ["python", "manage.py", "consume_dlq"]`, biến môi trường DB và RabbitMQ giống `payment-consumer`, `depends_on: payment-db (service_healthy) + rabbitmq (service_healthy)`, `restart: unless-stopped`, `volumes: ./common:/app/common`, `networks: Ecommerce-net`.
  - Requirements: 3.7, 3.8
  - Depends on: 3

- [x] 6. Tạo E2E test script – Cấu trúc cơ bản, dry-run và các bước HTTP
  Tạo `scripts/e2e_test.py` hoàn chỉnh với: imports (`os`, `sys`, `time`, `random`, `string`, `argparse`, `requests`), hằng số (`BASE_URL`, `MAX_POLL=10`, `POLL_INTERVAL=2`, ANSI color codes), `StepResult` namedtuple, hàm `print_step`/`print_summary`, hàm `random_user()`. Triển khai 8 hàm bước: `step_register`, `step_login`, `step_get_products`, `step_add_to_cart`, `step_checkout`, `step_pay`, `step_poll_payment`, `step_poll_shipping`. Poll retry tối đa 10 lần, sleep 2s. Dùng `requests.Session` với `Authorization: Bearer {token}`, `timeout=10`. Flag `--dry-run` bỏ qua HTTP calls. `sys.exit(0)` nếu pass, `sys.exit(1)` nếu fail.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
