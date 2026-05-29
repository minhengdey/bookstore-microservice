-- ============================================================
-- cart_db – Dữ liệu mẫu (carts, cart_items)
-- Chạy: psql -U postgres -d cart_db -f 05_cart_db_seed.sql
-- ============================================================

TRUNCATE cart_items, carts RESTART IDENTITY CASCADE;

INSERT INTO carts (id, customer_id, created_date) VALUES
(1, 1, NOW()),
(2, 2, NOW()),
(3, 3, NOW());

INSERT INTO cart_items (id, cart_id, book_id, quantity, unit_price) VALUES
(1, 1, 1, 1, 1890000),
(2, 1, 7, 1, 890000),
(3, 2, 4, 1, 6990000),
(4, 2, 6, 1, 2790000),
(5, 3, 9, 2, 520000),
(6, 3, 12, 1, 240000);

SELECT setval(pg_get_serial_sequence('carts', 'id'), 3);
SELECT setval(pg_get_serial_sequence('cart_items', 'id'), 6);
