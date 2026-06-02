-- ============================================================
-- recommender_db – Dữ liệu mẫu (recommendation_logs)
-- Chạy: psql -U postgres -d recommender_db -f 11_recommender_db_seed.sql
-- ============================================================

TRUNCATE recommendation_logs RESTART IDENTITY CASCADE;

INSERT INTO recommendation_logs (id, customer_id, product_ids, created_at, strategy) VALUES
(1, 1, '[4, 6, 11]', NOW(), 'collaborative'),
(2, 2, '[1, 9, 10]', NOW(), 'content_based'),
(3, 3, '[8, 12, 7]', NOW(), 'hybrid'),
(4, 1, '[2, 5, 7]', NOW(), 'trending');

SELECT setval(pg_get_serial_sequence('recommendation_logs', 'id'), COALESCE((SELECT MAX(id) FROM recommendation_logs), 1));
