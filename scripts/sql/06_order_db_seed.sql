-- ============================================================
-- order_db – Dữ liệu mẫu (discounts, orders, order_items, order_discounts, invoices, coupons)
-- Chạy: psql -U postgres -d order_db -f 06_order_db_seed.sql
-- ============================================================

TRUNCATE invoices, order_discounts, order_items, orders, coupons, discounts RESTART IDENTITY CASCADE;

INSERT INTO discounts (id, discount_code, discount_name, description, start_date, end_date, discount_value, is_percentage, is_active) VALUES
(1, 'GIAM10', 'Giảm 10%', 'Áp dụng đơn từ 200k', CURRENT_DATE, CURRENT_DATE + 30, 10, true, true),
(2, 'FIX50K', 'Giảm 50.000đ', '', CURRENT_DATE, CURRENT_DATE + 30, 50000, false, true);

INSERT INTO orders (id, customer_id, order_date, status, shipping_fee, discount_amount, total_amount, admin_id, notes) VALUES
(1, 1, NOW(), 'confirmed', 25000, 250000, 9045000, 1, 'Đơn đặt combo điện tử và gia dụng'),
(2, 2, NOW(), 'delivered', 25000, 0, 2355000, 1, 'Đơn chăm sóc cá nhân và tiện ích'),
(3, 3, NOW(), 'processing', 25000, 50000, 1665000, 1, 'Đơn mua đồ thể thao và tiêu dùng');

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount) VALUES
(1, 1, 1, 1, 1890000, 0),
(2, 1, 4, 1, 6990000, 0),
(3, 1, 11, 1, 390000, 0),
(4, 2, 9, 2, 520000, 0),
(5, 2, 10, 1, 1290000, 0),
(6, 3, 8, 1, 1450000, 0),
(7, 3, 12, 1, 240000, 0);

INSERT INTO order_discounts (id, order_id, discount_id, applied_value) VALUES (1, 1, 1, 10);

INSERT INTO invoices (id, order_id, created_date, due_date, description, status, admin_id) VALUES
(1, 1, NOW(), CURRENT_DATE + 7, '', 'issued', 1),
(2, 2, NOW(), NULL, '', 'paid', NULL),
(3, 3, NOW(), CURRENT_DATE + 7, '', 'issued', 1);

INSERT INTO coupons (id, customer_id, order_id, coupon_code, discount_value, is_percentage, expiry_date, status) VALUES
(1, 1, NULL, 'WELCOME01', 15, true, CURRENT_DATE + 30, 'active');

SELECT setval(pg_get_serial_sequence('discounts', 'id'), COALESCE((SELECT MAX(id) FROM discounts), 1));
SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE((SELECT MAX(id) FROM orders), 1));
SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE((SELECT MAX(id) FROM order_items), 1));
SELECT setval(pg_get_serial_sequence('order_discounts', 'id'), COALESCE((SELECT MAX(id) FROM order_discounts), 1));
SELECT setval(pg_get_serial_sequence('invoices', 'id'), COALESCE((SELECT MAX(id) FROM invoices), 1));
SELECT setval(pg_get_serial_sequence('coupons', 'id'), COALESCE((SELECT MAX(id) FROM coupons), 1));
