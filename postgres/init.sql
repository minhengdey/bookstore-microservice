-- ============================================================
-- BookStore Microservice – PostgreSQL Database Initialization
-- Script này chạy tự động khi postgres container khởi động lần đầu
-- Dùng user 'postgres' (superuser mặc định) — không cần GRANT riêng
-- ============================================================

CREATE DATABASE customer_db;
CREATE DATABASE book_db;
CREATE DATABASE catalog_db;
CREATE DATABASE cart_db;
CREATE DATABASE staff_db;
CREATE DATABASE manager_db;
CREATE DATABASE order_db;
CREATE DATABASE pay_db;
CREATE DATABASE ship_db;
CREATE DATABASE comment_rate_db;
CREATE DATABASE recommender_db;
