-- ============================================================
-- customer_db – Dữ liệu mẫu (users, customers, web_addresses)
-- Chạy: psql -U postgres -d customer_db -f 01_customer_db_seed.sql
-- Lưu ý: password dùng hash Django; để đăng nhập được hãy chạy
--   python manage.py seed_mock trong customer-service (hoặc cập nhật password sau).
-- ============================================================

TRUNCATE web_addresses, customers, users RESTART IDENTITY CASCADE;

-- Password: password123 (Django PBKDF2 – nếu import thuần SQL, đăng nhập cần chạy seed_mock)
INSERT INTO users (id, username, email, password, phone, is_active, created_date) VALUES
(1, 'customer1', 'customer1@example.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0901111111', true, NOW()),
(2, 'customer2', 'customer2@example.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0902222222', true, NOW()),
(3, 'customer3', 'customer3@example.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0903333333', true, NOW());

INSERT INTO customers (id, user_id, loyalty_points, created_date) VALUES
(1, 1, 0, NOW()),
(2, 2, 0, NOW()),
(3, 3, 0, NOW());

INSERT INTO web_addresses (customer_id, recipient_name, address_line, city, state, country, postal_code, phone, is_default) VALUES
(1, 'customer1', '123 Đường ABC', 'TP.HCM', '', 'Vietnam', '700000', '0901111111', true),
(2, 'customer2', '123 Đường ABC', 'TP.HCM', '', 'Vietnam', '700000', '0902222222', true),
(3, 'customer3', '123 Đường ABC', 'TP.HCM', '', 'Vietnam', '700000', '0903333333', true);

SELECT setval(pg_get_serial_sequence('users', 'id'), 3);
SELECT setval(pg_get_serial_sequence('customers', 'id'), 3);
