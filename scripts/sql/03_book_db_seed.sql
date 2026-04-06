-- ============================================================
-- book_db – Dữ liệu mẫu (books, book_authors, book_categories, book_genres, book_publishers, book_images, book_conditions, book_languages)
-- Chạy: psql -U postgres -d book_db -f 03_book_db_seed.sql
-- ============================================================

TRUNCATE book_languages, book_conditions, book_images, book_publishers, book_genres, book_categories, book_authors, books RESTART IDENTITY CASCADE;

INSERT INTO books (id, title, isbn, description, publication_year, page_count, list_price, sale_price, stock, status, created_date, updated_date) VALUES
(1, 'Cho tôi xin một vé đi tuổi thơ', '9786041110910', 'Tác phẩm về ký ức tuổi thơ trong trẻo, cách nhìn thế giới giàu cảm xúc và bài học trưởng thành nhẹ nhàng.', 2020, 250, 80000, 72000, 100, 'active', NOW(), NOW()),
(2, 'Mắt biếc', '9786041110921', 'Tiểu thuyết tình cảm nổi tiếng với bối cảnh làng quê, học đường và những rung động đầu đời.', 2020, 250, 75000, 68000, 80, 'active', NOW(), NOW()),
(3, 'Nhà giả kim', '9786041110932', 'Câu chuyện hành trình theo đuổi vận mệnh cá nhân, truyền cảm hứng về ước mơ và lòng kiên định.', 2020, 250, 99000, 89000, 50, 'active', NOW(), NOW()),
(4, 'Rừng Na Uy', '9786041110943', 'Tiểu thuyết đương đại về cô đơn, tình yêu và những biến chuyển tâm lý trong tuổi trưởng thành.', 2020, 250, 120000, 108000, 40, 'active', NOW(), NOW()),
(5, 'Điều kỳ diệu của tiệm tạp hóa Namiya', '9786041110954', 'Tác phẩm chữa lành qua những lá thư và lựa chọn cuộc đời, kết nối nhiều số phận theo cách ấm áp.', 2020, 250, 110000, 99000, 30, 'active', NOW(), NOW());

INSERT INTO book_authors (book_id, author_id) VALUES (1, 1), (2, 1), (3, 2), (4, 3), (5, 3);
INSERT INTO book_categories (book_id, category_id) VALUES (1, 1), (2, 2), (3, 3), (4, 4), (5, 1);
INSERT INTO book_genres (book_id, genre_id) VALUES (1, 1), (2, 2), (3, 3), (4, 1), (5, 1);
INSERT INTO book_publishers (book_id, publisher_id) VALUES (1, 1), (2, 1), (3, 2), (4, 3), (5, 2);
INSERT INTO book_images (book_id, image_url, is_primary) VALUES (1, '/static/books/1.jpg', true), (2, '/static/books/2.jpg', true), (3, '/static/books/3.jpg', true), (4, '/static/books/4.jpg', true), (5, '/static/books/5.jpg', true);
INSERT INTO book_conditions (book_id, format, format_price, book_condition) VALUES (1, 'Paperback', 72000, 'New'), (2, 'Paperback', 68000, 'New'), (3, 'Paperback', 89000, 'New'), (4, 'Paperback', 108000, 'New'), (5, 'Paperback', 99000, 'New');
INSERT INTO book_languages (book_id, language_name) VALUES (1, 'Tiếng Việt'), (2, 'Tiếng Việt'), (3, 'Tiếng Việt'), (4, 'Tiếng Việt'), (5, 'Tiếng Việt');

SELECT setval(pg_get_serial_sequence('books', 'id'), 5);
