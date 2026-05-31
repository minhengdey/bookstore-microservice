-- ============================================================
-- user_db – Dữ liệu mẫu (users, customer_profiles, web_addresses)
-- Chạy: psql -U postgres -d user_db -f 13_user_db_seed.sql
-- ============================================================

TRUNCATE web_addresses, customer_profiles, staff_profiles, users RESTART IDENTITY CASCADE;

INSERT INTO users (id, username, email, password, phone, role, is_active, created_date) VALUES
(1, 'alice', 'alice@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', '0123456789', 'customer', true, NOW()),
(2, 'bob', 'bob@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', '0987654321', 'customer', true, NOW()),
(3, 'carol', 'carol@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', '0912345678', 'staff', true, NOW());

INSERT INTO customer_profiles (id, user_id, loyalty_points) VALUES
(1, 1, 120),
(2, 2, 35);

INSERT INTO staff_profiles (id, user_id, storage_code, department, position) VALUES
(1, 3, 'WH-01', 'Logistics', 'Warehouse Manager');

INSERT INTO web_addresses (id, customer_id, recipient_name, address_line, city, state, country, postal_code, phone, is_default) VALUES
(1, 1, 'Alice Nguyen', '123 Le Loi', 'Hanoi', '', 'VN', '100000', '0123456789', true),
(2, 2, 'Bob Tran', '456 Tran Phu', 'Hanoi', '', 'VN', '100001', '0987654321', true);

SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1));
SELECT setval(pg_get_serial_sequence('customer_profiles', 'id'), COALESCE((SELECT MAX(id) FROM customer_profiles), 1));
SELECT setval(pg_get_serial_sequence('staff_profiles', 'id'), COALESCE((SELECT MAX(id) FROM staff_profiles), 1));
SELECT setval(pg_get_serial_sequence('web_addresses', 'id'), COALESCE((SELECT MAX(id) FROM web_addresses), 1));
