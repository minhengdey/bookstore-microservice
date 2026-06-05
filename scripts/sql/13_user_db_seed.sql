-- ============================================================
-- user_db – Dữ liệu mẫu (users, customer_profiles, web_addresses)
-- Chạy: psql -U postgres -d user_db -f 13_user_db_seed.sql
-- ============================================================

TRUNCATE web_addresses, customer_profiles, staff_profiles, user_profiles, user_roles RESTART IDENTITY CASCADE;

INSERT INTO user_profiles (auth_user_id, status, role_version, full_name, phone, avatar_url, gender, created_at, updated_at) VALUES
('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'ACTIVE', 1, 'System Admin', '0000000000', '', 'Other', NOW(), NOW()),
('b3b3b3b3-b3b3-b3b3-b3b3-b3b3b3b3b3b3', 'ACTIVE', 1, 'Alice Nguyen', '0123456789', '', 'Female', NOW(), NOW()),
('c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', 'ACTIVE', 1, 'Bob Tran', '0987654321', '', 'Male', NOW(), NOW()),
('d5d5d5d5-d5d5-d5d5-d5d5-d5d5d5d5d5d5', 'ACTIVE', 1, 'Carol Nguyen', '0912345678', '', 'Female', NOW(), NOW());

INSERT INTO user_roles (userprofile_id, role_id) SELECT 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', id FROM roles WHERE name = 'ADMIN';
INSERT INTO user_roles (userprofile_id, role_id) SELECT 'b3b3b3b3-b3b3-b3b3-b3b3-b3b3b3b3b3b3', id FROM roles WHERE name = 'CUSTOMER';
INSERT INTO user_roles (userprofile_id, role_id) SELECT 'c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', id FROM roles WHERE name = 'CUSTOMER';
INSERT INTO user_roles (userprofile_id, role_id) SELECT 'd5d5d5d5-d5d5-d5d5-d5d5-d5d5d5d5d5d5', id FROM roles WHERE name = 'STAFF';

INSERT INTO customer_profiles (id, user_profile_id, loyalty_points) VALUES
(1, 'b3b3b3b3-b3b3-b3b3-b3b3-b3b3b3b3b3b3', 120),
(2, 'c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', 35);

INSERT INTO staff_profiles (id, user_profile_id, storage_code, department, position) VALUES
(1, 'd5d5d5d5-d5d5-d5d5-d5d5-d5d5d5d5d5d5', 'WH-01', 'Logistics', 'Warehouse Manager'),
(2, 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'HQ', 'IT', 'System Administrator');

INSERT INTO web_addresses (id, customer_id, recipient_name, address_line, city, state, country, postal_code, phone, is_default) VALUES
(1, 1, 'Alice Nguyen', '123 Le Loi', 'Hanoi', '', 'VN', '100000', '0123456789', true),
(2, 2, 'Bob Tran', '456 Tran Phu', 'Hanoi', '', 'VN', '100001', '0987654321', true);

SELECT setval(pg_get_serial_sequence('customer_profiles', 'id'), COALESCE((SELECT MAX(id) FROM customer_profiles), 1));
SELECT setval(pg_get_serial_sequence('staff_profiles', 'id'), COALESCE((SELECT MAX(id) FROM staff_profiles), 1));
SELECT setval(pg_get_serial_sequence('web_addresses', 'id'), COALESCE((SELECT MAX(id) FROM web_addresses), 1));
