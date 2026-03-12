-- ============================================================
-- comment_rate_db – Dữ liệu mẫu (book_reviews)
-- Chạy: psql -U postgres -d comment_rate_db -f 10_comment_rate_db_seed.sql
-- ============================================================

TRUNCATE book_reviews RESTART IDENTITY CASCADE;

INSERT INTO book_reviews (id, book_id, customer_id, reviews_text, rating, created_date, status) VALUES
(1, 1, 1, 'Sách hay, đáng đọc!', 5, NOW(), 'approved'),
(2, 1, 2, 'Rất cảm động.', 4, NOW(), 'approved'),
(3, 2, 1, 'Tác phẩm hay của Nguyễn Nhật Ánh.', 5, NOW(), 'approved'),
(4, 2, 3, 'Phù hợp thiếu nhi.', 4, NOW(), 'approved'),
(5, 3, 1, 'Câu chuyện ý nghĩa.', 5, NOW(), 'approved'),
(6, 3, 2, 'Đã đọc nhiều lần.', 5, NOW(), 'approved'),
(7, 4, 2, 'Rất thích phong cách Murakami.', 4, NOW(), 'approved'),
(8, 5, 3, 'Đáng suy ngẫm.', 4, NOW(), 'approved');

SELECT setval(pg_get_serial_sequence('book_reviews', 'id'), 8);
