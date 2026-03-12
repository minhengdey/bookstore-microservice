-- ============================================================
-- recommender_db – Dữ liệu mẫu (recommendation_logs)
-- Chạy: psql -U postgres -d recommender_db -f 11_recommender_db_seed.sql
-- ============================================================

TRUNCATE recommendation_logs RESTART IDENTITY CASCADE;

INSERT INTO recommendation_logs (id, customer_id, book_ids, created_at, strategy) VALUES
(1, 1, '[2, 3, 4]', NOW(), 'collaborative'),
(2, 2, '[1, 3, 5]', NOW(), 'content_based'),
(3, 3, '[1, 2, 4]', NOW(), 'collaborative');

SELECT setval(pg_get_serial_sequence('recommendation_logs', 'id'), 3);
