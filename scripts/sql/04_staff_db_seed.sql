-- ============================================================
-- staff_db – Dữ liệu mẫu (staff_users, inventory_staff)
-- Chạy: psql -U postgres -d staff_db -f 04_staff_db_seed.sql
-- Password: dùng Django seed_mock để đăng nhập được (hash đúng).
-- ============================================================

TRUNCATE inventory_staff, staff_users RESTART IDENTITY CASCADE;

INSERT INTO staff_users (id, username, email, password, phone, is_active, created_date) VALUES
(1, 'staff1', 'staff1@bookstore.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0911111111', true, NOW()),
(2, 'staff2', 'staff2@bookstore.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0922222222', true, NOW()),
(3, 'manager1', 'manager1@bookstore.com', 'pbkdf2_sha256$600000$seedsalt12345678901234567890$dGVzdA==', '0933333333', true, NOW());

INSERT INTO inventory_staff (id, user_id, storage_code, department, position, role) VALUES
(1, 1, 'STF001', 'Kho', 'Nhân viên kho', 'staff'),
(2, 2, 'STF002', 'Kho', 'Nhân viên kho', 'staff'),
(3, 3, 'STF003', 'Kho', 'Quản lý', 'manager');

SELECT setval(pg_get_serial_sequence('staff_users', 'id'), 3);
SELECT setval(pg_get_serial_sequence('inventory_staff', 'id'), 3);
