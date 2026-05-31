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
SELECT format('CREATE DATABASE %I', db_name)
FROM (VALUES
    ('auth_db'),
    ('user_db'),
    ('customer_db'),
    ('product_db'),
    ('catalog_db'),
    ('book_db'),
    ('cart_db'),
    ('order_db'),
    ('pay_db'),
    ('ship_db'),
    ('staff_db'),
    ('manager_db'),
    ('comment_rate_db'),
    ('recommender_db')
) AS dbs(db_name)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = db_name
)
\gexec

-- Xác nhận đã tạo thành công
SELECT datname AS "Database đã tạo"
FROM pg_database
WHERE datname IN (
    'auth_db','user_db','customer_db','product_db','catalog_db','book_db',
    'cart_db','order_db','pay_db','ship_db','staff_db','manager_db',
    'comment_rate_db','recommender_db'
)
ORDER BY datname;
