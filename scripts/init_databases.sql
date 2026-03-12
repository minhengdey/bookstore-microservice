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

-- Tạo 11 databases (mỗi microservice 1 DB riêng)
CREATE DATABASE customer_db;
CREATE DATABASE book_db;
CREATE DATABASE catalog_db;
CREATE DATABASE cart_db;
CREATE DATABASE staff_db;
CREATE DATABASE manager_db;
CREATE DATABASE order_db;
CREATE DATABASE pay_db;
CREATE DATABASE ship_db;
CREATE DATABASE comment_rate_db;
CREATE DATABASE recommender_db;

-- Xác nhận đã tạo thành công
SELECT datname AS "Database đã tạo"
FROM pg_database
WHERE datname IN (
    'customer_db','book_db','catalog_db','cart_db',
    'staff_db','manager_db','order_db','pay_db',
    'ship_db','comment_rate_db','recommender_db'
)
ORDER BY datname;
