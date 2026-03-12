-- ============================================================
-- order_db – Dữ liệu mẫu (discounts, orders, order_items, order_discounts, invoices, coupons)
-- Chạy: psql -U postgres -d order_db -f 06_order_db_seed.sql
-- ============================================================

TRUNCATE invoices, order_discounts, order_items, orders, coupons, discounts RESTART IDENTITY CASCADE;

INSERT INTO discounts (id, discount_code, discount_name, description, start_date, end_date, discount_value, is_percentage, is_active) VALUES
(1, 'GIAM10', 'Giảm 10%', 'Áp dụng đơn từ 200k', CURRENT_DATE, CURRENT_DATE + 30, 10, true, true),
(2, 'FIX50K', 'Giảm 50.000đ', '', CURRENT_DATE, CURRENT_DATE + 30, 50000, false, true);

INSERT INTO orders (id, customer_id, order_date, status, shipping_fee, discount_amount, total_amount, admin_id, notes) VALUES
(1, 1, NOW(), 'confirmed', 15000, 7200, 150800, 1, ''),
(2, 2, NOW(), 'delivered', 15000, 0, 83000, 1, '');

INSERT INTO order_items (id, order_id, book_id, quantity, unit_price, discount) VALUES
(1, 1, 1, 2, 72000, 0),
(2, 1, 3, 1, 89000, 0),
(3, 2, 2, 1, 68000, 0);

INSERT INTO order_discounts (id, order_id, discount_id, applied_value) VALUES (1, 1, 1, 10);

INSERT INTO invoices (id, order_id, created_date, due_date, description, status, admin_id) VALUES
(1, 1, NOW(), CURRENT_DATE + 7, '', 'issued', 1),
(2, 2, NOW(), NULL, '', 'paid', NULL);

INSERT INTO coupons (id, customer_id, order_id, coupon_code, discount_value, is_percentage, expiry_date, status) VALUES
(1, 1, NULL, 'WELCOME01', 15, true, CURRENT_DATE + 30, 'active');

SELECT setval(pg_get_serial_sequence('discounts', 'id'), 2);
SELECT setval(pg_get_serial_sequence('orders', 'id'), 2);
SELECT setval(pg_get_serial_sequence('order_items', 'id'), 3);
SELECT setval(pg_get_serial_sequence('invoices', 'id'), 2);
SELECT setval(pg_get_serial_sequence('coupons', 'id'), 1);
