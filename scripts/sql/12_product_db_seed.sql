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

INSERT INTO products (id, name, category_id, price, currency, sku, image_url, attributes, description, status, stock) VALUES
(1, 'Tai nghe khử ồn SoundPulse X2', 1, 1890000, 'VND', 'ELC-HP-X2', '/static/product-images/electronics.svg', '{"brand":"SoundPulse","color":"Black","features":["Bluetooth 5.3","Active Noise Cancelling","30h battery"]}'::jsonb, 'Tai nghe không dây cho nghe nhạc, làm việc và di chuyển hằng ngày.', 'active', 120),
(2, 'Đồng hồ thông minh FitTrack S1', 1, 2490000, 'VND', 'ELC-SW-S1', '/static/product-images/electronics.svg', '{"brand":"FitTrack","color":"Graphite","features":["Heart rate","Sleep tracking","GPS"]}'::jsonb, 'Đồng hồ theo dõi sức khỏe và luyện tập với màn hình AMOLED.', 'active', 80),
(3, 'Bàn phím cơ SwiftKeys Pro', 1, 1690000, 'VND', 'ELC-KB-PRO', '/static/product-images/electronics.svg', '{"brand":"SwiftKeys","switch":"Brown","layout":"75%","connectivity":["Bluetooth","2.4GHz","USB-C"]}'::jsonb, 'Bàn phím cơ đa kết nối cho dân văn phòng và game thủ.', 'active', 95),
(4, 'Màn hình cong UltraView 27Q', 1, 4890000, 'VND', 'ELC-MN-27Q', '/static/product-images/electronics.svg', '{"brand":"UltraView","size":"27 inch","resolution":"2K","refresh_rate":"165Hz"}'::jsonb, 'Màn hình cong cho làm việc đa nhiệm và giải trí mượt mà.', 'active', 45),
(5, 'Robot hút bụi CleanBot 3000', 2, 6990000, 'VND', 'HOM-RB-3000', '/static/product-images/home.svg', '{"brand":"CleanBot","suction":"4000Pa","features":["Auto mapping","Wet mop","App control"]}'::jsonb, 'Robot hút bụi tự động giúp dọn dẹp nhà cửa gọn gàng hơn.', 'active', 40),
(6, 'Nồi chiên không dầu CrispAir 5L', 2, 2790000, 'VND', 'HOM-AF-5L', '/static/product-images/home.svg', '{"brand":"CrispAir","capacity":"5L","features":["Rapid air","Non-stick basket","8 presets"]}'::jsonb, 'Nồi chiên cho bữa ăn ít dầu mỡ nhưng vẫn giòn ngon.', 'active', 70),
(7, 'Máy pha cà phê Aroma Brew Mini', 2, 3290000, 'VND', 'HOM-CF-MINI', '/static/product-images/home.svg', '{"brand":"Aroma Brew","capacity":"1.2L","features":["Auto shut-off","Keep warm","Compact design"]}'::jsonb, 'Máy pha cà phê nhỏ gọn cho gia đình và văn phòng.', 'active', 55),
(8, 'Máy xay sinh tố FreshBlend Pro', 2, 1490000, 'VND', 'HOM-BL-FPRO', '/static/product-images/home.svg', '{"brand":"FreshBlend","power":"1000W","jar":"1.5L","features":["Ice crushing","5 speeds","Stainless blades"]}'::jsonb, 'Máy xay đa năng cho sinh tố, súp và đồ uống nhanh.', 'active', 62),
(9, 'Áo khoác gió UrbanFlex', 3, 890000, 'VND', 'FAS-JK-URB', '/static/product-images/fashion.svg', '{"brand":"UrbanFlex","size":"L","material":"Polyester","gender":"Unisex"}'::jsonb, 'Áo khoác nhẹ, dễ phối đồ cho đi làm và đi chơi.', 'active', 110),
(10, 'Giày chạy bộ RunLite 2.0', 5, 1450000, 'VND', 'SPT-SH-RL20', '/static/product-images/sports.svg', '{"brand":"RunLite","size_range":"39-44","features":["Lightweight","Breathable mesh","Energy return foam"]}'::jsonb, 'Giày chạy bộ phù hợp tập luyện, đi bộ và marathon ngắn.', 'active', 60),
(11, 'Túi tote CanvasCarry', 3, 450000, 'VND', 'FAS-BG-TOTE', '/static/product-images/fashion.svg', '{"brand":"CanvasCarry","material":"Canvas","style":"Tote","features":["Large capacity","Minimal design"]}'::jsonb, 'Túi tote canvas tiện dụng cho đi học, đi làm và mua sắm.', 'active', 140),
(12, 'Áo thun basic SoftCotton', 3, 320000, 'VND', 'FAS-TS-SCOT', '/static/product-images/fashion.svg', '{"brand":"SoftCotton","size":"M","material":"Cotton","fit":"Regular"}'::jsonb, 'Áo thun basic dễ phối, phù hợp mặc hằng ngày.', 'active', 210),
(13, 'Serum Vitamin C GlowLab', 4, 520000, 'VND', 'BTY-SR-CGLOW', '/static/product-images/beauty.svg', '{"brand":"GlowLab","volume":"30ml","features":["Vitamin C","Niacinamide","Brightening"]}'::jsonb, 'Serum chăm sóc da hỗ trợ làm sáng và đều màu da.', 'active', 150),
(14, 'Máy sấy tóc IonicCare', 4, 1290000, 'VND', 'BTY-HD-ION', '/static/product-images/beauty.svg', '{"brand":"IonicCare","power":"1800W","features":["Ionic care","3 heat settings","Foldable handle"]}'::jsonb, 'Máy sấy tóc gọn nhẹ, phù hợp nhu cầu chăm sóc cá nhân tại nhà.', 'active', 65),
(15, 'Sữa rửa mặt GentleClean', 4, 210000, 'VND', 'BTY-FC-GENT', '/static/product-images/beauty.svg', '{"brand":"GentleClean","volume":"150ml","skin_type":"Sensitive","features":["Low pH","No fragrance"]}'::jsonb, 'Sữa rửa mặt dịu nhẹ cho chu trình chăm sóc da hàng ngày.', 'active', 180),
(16, 'Son dưỡng ColorPop', 4, 180000, 'VND', 'BTY-LP-CPOP', '/static/product-images/beauty.svg', '{"brand":"ColorPop","shade":"Rose","features":["Moisturizing","Shea butter"]}'::jsonb, 'Son dưỡng có màu nhẹ, cấp ẩm và làm mềm môi.', 'active', 260),
(17, 'Bình giữ nhiệt SteelGo 750ml', 5, 390000, 'VND', 'SPT-BT-750', '/static/product-images/sports.svg', '{"brand":"SteelGo","capacity":"750ml","material":"Stainless steel","features":["Vacuum insulation","Leak proof"]}'::jsonb, 'Bình giữ nhiệt mang đi làm, đi học hoặc tập luyện.', 'active', 180),
(18, 'Thảm yoga FlexMat', 5, 540000, 'VND', 'SPT-YG-FLEX', '/static/product-images/sports.svg', '{"brand":"FlexMat","thickness":"8mm","material":"TPE","features":["Non-slip","Lightweight"]}'::jsonb, 'Thảm yoga êm, bám sàn tốt cho tập luyện tại nhà.', 'active', 95),
(19, 'Bóng đá training ProKick', 5, 330000, 'VND', 'SPT-BL-PKICK', '/static/product-images/sports.svg', '{"brand":"ProKick","size":"5","material":"PU","features":["Machine stitched","Outdoor training"]}'::jsonb, 'Bóng đá luyện tập cho sân cỏ nhân tạo và hoạt động thể thao.', 'active', 135),
(20, 'Tai nghe thể thao PulseRun', 5, 760000, 'VND', 'SPT-HP-PRUN', '/static/product-images/sports.svg', '{"brand":"PulseRun","features":["Sweat resistant","Ear hooks","Bluetooth 5.3"]}'::jsonb, 'Tai nghe thể thao ôm tai chắc chắn, phù hợp chạy bộ và tập gym.', 'active', 88),
(21, 'Hạt cà phê rang xay Morning Roast 500g', 6, 240000, 'VND', 'GRC-CF-500', '/static/product-images/grocery.svg', '{"brand":"Morning Roast","weight":"500g","origin":"Đà Lạt","roast_level":"Medium"}'::jsonb, 'Hạt cà phê rang xay phục vụ gia đình, văn phòng và quán nhỏ.', 'active', 220),
(22, 'Yến mạch nguyên cám NutriOats', 6, 160000, 'VND', 'GRC-OT-NUTO', '/static/product-images/grocery.svg', '{"brand":"NutriOats","weight":"1kg","features":["Whole grain","High fiber"]}'::jsonb, 'Yến mạch dinh dưỡng cho bữa sáng lành mạnh.', 'active', 240),
(23, 'Mì ramen vị miso Tokyo Bowl', 6, 99000, 'VND', 'GRC-RM-TOK', '/static/product-images/grocery.svg', '{"brand":"Tokyo Bowl","pack":"5 packs","flavor":"Miso"}'::jsonb, 'Mì ramen ăn liền hương vị Nhật Bản tiện lợi.', 'active', 300),
(24, 'Bánh quy yến mạch DailyBite', 6, 135000, 'VND', 'GRC-CK-DBITE', '/static/product-images/grocery.svg', '{"brand":"DailyBite","weight":"350g","features":["Low sugar","Whole oats"]}'::jsonb, 'Bánh quy giòn nhẹ cho bữa phụ hoặc quà tặng.', 'active', 190);

SELECT setval(pg_get_serial_sequence('categories', 'id'), COALESCE((SELECT MAX(id) FROM categories), 1));
SELECT setval(pg_get_serial_sequence('products', 'id'), COALESCE((SELECT MAX(id) FROM products), 1));