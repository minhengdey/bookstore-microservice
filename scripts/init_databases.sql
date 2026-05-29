-- ==============================================================
-- BookStore Microservice — Khởi tạo databases
-- Chạy file này trong DBeaver (hoặc psql) bằng user postgres
-- TRƯỚC KHI chạy docker compose up
-- ==============================================================
-- Cách chạy trong DBeaver:
--   1. Kết nối với user postgres
--   2. Mở file này (File → Open)
--   3. Bôi đen toàn bộ → F5 (Execute Script)
-- ==============================================================

-- Tạo databases (mỗi microservice 1 DB riêng)
CREATE DATABASE auth_db;
CREATE DATABASE user_db;
CREATE DATABASE product_db;
CREATE DATABASE cart_db;
CREATE DATABASE order_db;
CREATE DATABASE pay_db;
CREATE DATABASE ship_db;
CREATE DATABASE recommender_db;

-- Xác nhận đã tạo thành công
SELECT datname AS "Database đã tạo"
FROM pg_database
WHERE datname IN (
    'auth_db','user_db','product_db','cart_db',
    'order_db','pay_db','ship_db','recommender_db'
)
ORDER BY datname;
