-- ============================================================
-- ship_db – Dữ liệu mẫu (shipping_methods, shipping_features, shippings, shipping_addresses, shipping_statuses)
-- Chạy: psql -U postgres -d ship_db -f 08_ship_db_seed.sql
-- ============================================================

TRUNCATE shipping_statuses, shipping_addresses, shippings, shipping_features, shipping_methods RESTART IDENTITY CASCADE;

INSERT INTO shipping_methods (id, method_name, description, min_weight, max_weight, min_distance, max_distance, rate) VALUES
(1, 'Giao hàng tiêu chuẩn', '3-5 ngày', 0, 5000, 0, 500, 15000),
(2, 'Giao hàng nhanh', '1-2 ngày', 0, 0, 0, 0, 30000);

INSERT INTO shipping_features (id, shipping_method_id, feature, value) VALUES
(1, 1, 'speed', '3-5 days'),
(2, 2, 'speed', '1-2 days');

INSERT INTO shippings (id, order_id, shipping_method_id, status, estimated_delivery_date, created_date) VALUES
(1, 1, 1, 'shipped', CURRENT_DATE + 3, NOW()),
(2, 2, 1, 'delivered', CURRENT_DATE + 3, NOW());

INSERT INTO shipping_addresses (id, shipping_id, recipient_name, address_line, city, state, country, postal_code, phone, updated_date) VALUES
(1, 1, 'Customer 1', '123 Đường ABC', 'TP.HCM', '', 'Vietnam', '700000', '0900000000', NOW()),
(2, 2, 'Customer 2', '123 Đường ABC', 'Hà Nội', '', 'Vietnam', '100000', '0900000000', NOW());

INSERT INTO shipping_statuses (id, shipping_id, status, description, updated_date) VALUES
(1, 1, 'shipped', 'Đang giao', NOW()),
(2, 2, 'delivered', 'Đã giao', NOW());

SELECT setval(pg_get_serial_sequence('shipping_methods', 'id'), 2);
SELECT setval(pg_get_serial_sequence('shippings', 'id'), 2);
