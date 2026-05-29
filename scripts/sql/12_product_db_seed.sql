-- ============================================================
-- product_db – Dữ liệu mẫu (categories, products)
-- Chạy: psql -U postgres -d product_db -f 12_product_db_seed.sql
-- ============================================================

TRUNCATE stock_reservation_logs, products, categories RESTART IDENTITY CASCADE;

INSERT INTO categories (id, name, description) VALUES
(1, 'Electronics', 'Thiết bị điện tử và phụ kiện thông minh'),
(2, 'Home Appliances', 'Thiết bị gia dụng cho nhà bếp và sinh hoạt'),
(3, 'Fashion', 'Thời trang, giày dép và phụ kiện'),
(4, 'Beauty & Personal Care', 'Chăm sóc cá nhân và làm đẹp'),
(5, 'Sports & Outdoors', 'Dụng cụ thể thao và hoạt động ngoài trời'),
(6, 'Grocery & Daily Essentials', 'Thực phẩm, đồ uống và nhu yếu phẩm');

INSERT INTO products (id, name, category_id, price, currency, sku, attributes, description, status, stock) VALUES
(1, 'Tai nghe khử ồn SoundPulse X2', 1, 1890000, 'VND', 'ELC-HP-X2', '{"brand":"SoundPulse","color":"Black","features":["Bluetooth 5.3","Active Noise Cancelling","30h battery"]}'::jsonb, 'Tai nghe không dây cho nghe nhạc, làm việc và di chuyển hằng ngày.', 'active', 120),
(2, 'Đồng hồ thông minh FitTrack S1', 1, 2490000, 'VND', 'ELC-SW-S1', '{"brand":"FitTrack","color":"Graphite","features":["Heart rate","Sleep tracking","GPS"]}'::jsonb, 'Đồng hồ theo dõi sức khỏe và luyện tập với màn hình AMOLED.', 'active', 80),
(3, 'Bàn phím cơ SwiftKeys Pro', 1, 1690000, 'VND', 'ELC-KB-PRO', '{"brand":"SwiftKeys","switch":"Brown","layout":"75%","connectivity":["Bluetooth","2.4GHz","USB-C"]}'::jsonb, 'Bàn phím cơ đa kết nối cho dân văn phòng và game thủ.', 'active', 95),
(4, 'Robot hút bụi CleanBot 3000', 2, 6990000, 'VND', 'HOM-RB-3000', '{"brand":"CleanBot","suction":"4000Pa","features":["Auto mapping","Wet mop","App control"]}'::jsonb, 'Robot hút bụi tự động giúp dọn dẹp nhà cửa gọn gàng hơn.', 'active', 40),
(5, 'Máy pha cà phê Aroma Brew Mini', 2, 3290000, 'VND', 'HOM-CF-MINI', '{"brand":"Aroma Brew","capacity":"1.2L","features":["Auto shut-off","Keep warm","Compact design"]}'::jsonb, 'Máy pha cà phê nhỏ gọn cho gia đình và văn phòng.', 'active', 55),
(6, 'Nồi chiên không dầu CrispAir 5L', 2, 2790000, 'VND', 'HOM-AF-5L', '{"brand":"CrispAir","capacity":"5L","features":["Rapid air","Non-stick basket","8 presets"]}'::jsonb, 'Nồi chiên cho bữa ăn ít dầu mỡ nhưng vẫn giòn ngon.', 'active', 70),
(7, 'Áo khoác gió UrbanFlex', 3, 890000, 'VND', 'FAS-JK-URB', '{"brand":"UrbanFlex","size":"L","material":"Polyester","gender":"Unisex"}'::jsonb, 'Áo khoác nhẹ, dễ phối đồ cho đi làm và đi chơi.', 'active', 110),
(8, 'Giày chạy bộ RunLite 2.0', 5, 1450000, 'VND', 'SPT-SH-RL20', '{"brand":"RunLite","size_range":"39-44","features":["Lightweight","Breathable mesh","Energy return foam"]}'::jsonb, 'Giày chạy bộ phù hợp tập luyện, đi bộ và marathon ngắn.', 'active', 60),
(9, 'Serum Vitamin C GlowLab', 4, 520000, 'VND', 'BTY-SR-CGLOW', '{"brand":"GlowLab","volume":"30ml","features":["Vitamin C","Niacinamide","Brightening"]}'::jsonb, 'Serum chăm sóc da hỗ trợ làm sáng và đều màu da.', 'active', 150),
(10, 'Máy sấy tóc IonicCare', 4, 1290000, 'VND', 'BTY-HD-ION', '{"brand":"IonicCare","power":"1800W","features":["Ionic care","3 heat settings","Foldable handle"]}'::jsonb, 'Máy sấy tóc gọn nhẹ, phù hợp nhu cầu chăm sóc cá nhân tại nhà.', 'active', 65),
(11, 'Bình giữ nhiệt SteelGo 750ml', 5, 390000, 'VND', 'SPT-BT-750', '{"brand":"SteelGo","capacity":"750ml","material":"Stainless steel","features":["Vacuum insulation","Leak proof"]}'::jsonb, 'Bình giữ nhiệt mang đi làm, đi học hoặc tập luyện.', 'active', 180),
(12, 'Hạt cà phê rang xay Morning Roast 500g', 6, 240000, 'VND', 'GRC-CF-500', '{"brand":"Morning Roast","weight":"500g","origin":"Đà Lạt","roast_level":"Medium"}'::jsonb, 'Hạt cà phê rang xay phục vụ gia đình, văn phòng và quán nhỏ.', 'active', 220);

SELECT setval(pg_get_serial_sequence('categories', 'id'), 6);
SELECT setval(pg_get_serial_sequence('products', 'id'), 12);