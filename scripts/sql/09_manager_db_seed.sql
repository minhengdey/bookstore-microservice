-- ============================================================
-- manager_db – Dữ liệu mẫu (warehouses, warehouse_locations, suppliers, inventories, purchase_orders, purchase_order_items, stock_movements, stock_movement_logs, stock_transfers)
-- Chạy: psql -U postgres -d manager_db -f 09_manager_db_seed.sql
-- ============================================================

TRUNCATE stock_movement_logs, stock_movements, stock_transfers, purchase_order_items, purchase_orders, inventories, warehouse_locations, warehouses, suppliers RESTART IDENTITY CASCADE;

INSERT INTO warehouses (id, warehouse_name, warehouse_code, address, phone, manager_id, capacity) VALUES
(1, 'Kho TP.HCM', 'WH-HCM01', 'Quận 12, TP.HCM', '0281234567', 1, 10000),
(2, 'Kho Hà Nội', 'WH-HN01', 'Đống Đa, Hà Nội', '0241234567', 1, 8000);

INSERT INTO warehouse_locations (id, warehouse_id, location_code, location_name, row_number, column_number, floor_number, capacity) VALUES
(1, 1, 'A-01-01', 'Kệ A tầng 1', 'A', '01', '1', 500),
(2, 2, 'B-01-01', 'Kệ B tầng 1', 'B', '01', '1', 400);

INSERT INTO suppliers (id, supplier_name, contact_name, email, phone, address, fax) VALUES
(1, 'Công ty Sách ABC', 'Nguyễn Văn A', 'abc@supplier.com', '0901234567', 'TP.HCM', ''),
(2, 'NXB Trẻ', 'Phòng kinh doanh', 'kinhdoanh@nxbtre.com.vn', '02839316266', '', '');

INSERT INTO inventories (id, book_id, warehouse_id, stock_quantity, min_quantity, max_quantity, last_updated) VALUES
(1, 1, 1, 60, 10, 200, NOW()), (2, 2, 1, 70, 10, 200, NOW()), (3, 3, 1, 80, 10, 200, NOW()), (4, 4, 1, 90, 10, 200, NOW()), (5, 5, 1, 100, 10, 200, NOW()),
(6, 1, 2, 30, 5, 100, NOW()), (7, 2, 2, 30, 5, 100, NOW()), (8, 3, 2, 30, 5, 100, NOW());

INSERT INTO purchase_orders (id, supplier_id, admin_id, expected_date, status, notes, total_amount, created_date) VALUES
(1, 1, 1, CURRENT_DATE, 'approved', 'Đơn nhập mẫu', 5000000, NOW());

INSERT INTO purchase_order_items (id, purchase_order_id, book_id, quantity, unit_price) VALUES
(1, 1, 1, 100, 50000),
(2, 1, 2, 80, 45000);

INSERT INTO stock_movements (id, book_id, from_warehouse_id, to_warehouse_id, quantity, movement_date, transfer_date, admin_id, notes) VALUES
(1, 1, NULL, 1, 100, NOW(), NULL, 1, 'Nhập từ PO');

INSERT INTO stock_movement_logs (id, movement_id, action, description, created_date) VALUES
(1, 1, 'RECEIVE', 'Nhập kho từ đơn mua', NOW());

INSERT INTO stock_transfers (id, from_warehouse_id, to_warehouse_id, book_id, quantity, transfer_date, admin_id, status) VALUES
(1, 1, 2, 1, 20, NOW(), 1, 'completed');

SELECT setval(pg_get_serial_sequence('warehouses', 'id'), 2);
SELECT setval(pg_get_serial_sequence('suppliers', 'id'), 2);
SELECT setval(pg_get_serial_sequence('purchase_orders', 'id'), 1);
