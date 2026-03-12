-- ============================================================
-- catalog_db – Dữ liệu mẫu (authors, categories, genres, publishers)
-- Chạy: psql -U postgres -d catalog_db -f 02_catalog_db_seed.sql
-- ============================================================

TRUNCATE publishers, genres, categories, authors RESTART IDENTITY CASCADE;

INSERT INTO authors (id, author_name, biography, birth_year, death_year) VALUES
(1, 'Nguyễn Nhật Ánh', 'Nhà văn Việt Nam', 1955, NULL),
(2, 'Paulo Coelho', 'Nhà văn Brazil', 1947, NULL),
(3, 'Haruki Murakami', 'Nhà văn Nhật Bản', 1949, NULL);

INSERT INTO categories (id, category_name, parent_category_id, description) VALUES
(1, 'Sách gốc', NULL, 'Sách không dịch'),
(2, 'Sách dịch', 1, 'Sách dịch'),
(3, 'Sách thiếu nhi', NULL, 'Cho trẻ em'),
(4, 'Sách văn học', NULL, 'Văn học trong nước và nước ngoài');

INSERT INTO genres (id, genre_name, description) VALUES
(1, 'Tiểu thuyết', 'Tiểu thuyết'),
(2, 'Truyện ngắn', 'Truyện ngắn'),
(3, 'Kỹ năng sống', 'Self-help'),
(4, 'Kinh doanh', 'Sách kinh doanh');

INSERT INTO publishers (id, publisher_name, contact_name, address, phone, website) VALUES
(1, 'NXB Trẻ', 'Phòng kinh doanh', 'TP.HCM', '02839316266', ''),
(2, 'NXB Kim Đồng', 'Liên hệ', 'Hà Nội', '02438221304', ''),
(3, 'NXB Hội Nhà văn', '', 'Hà Nội', '', '');

SELECT setval(pg_get_serial_sequence('authors', 'id'), 3);
SELECT setval(pg_get_serial_sequence('categories', 'id'), 4);
SELECT setval(pg_get_serial_sequence('genres', 'id'), 4);
SELECT setval(pg_get_serial_sequence('publishers', 'id'), 3);
