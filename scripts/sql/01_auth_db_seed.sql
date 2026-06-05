-- ============================================================
-- auth_db – Dữ liệu mẫu (auth_users)
-- ============================================================

TRUNCATE auth_users RESTART IDENTITY CASCADE;

INSERT INTO auth_users (id, username, email, password, is_active, is_staff, is_superuser, created_at, updated_at) VALUES
('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'admin', 'admin@ecommerce.local', 'pbkdf2_sha256$260000$fake$saltedhash', true, true, true, NOW(), NOW()),
('b3b3b3b3-b3b3-b3b3-b3b3-b3b3b3b3b3b3', 'alice', 'alice@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', true, false, false, NOW(), NOW()),
('c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', 'bob', 'bob@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', true, false, false, NOW(), NOW()),
('d5d5d5d5-d5d5-d5d5-d5d5-d5d5d5d5d5d5', 'carol', 'carol@example.com', 'pbkdf2_sha256$260000$fake$saltedhash', true, true, false, NOW(), NOW());
