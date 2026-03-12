-- ============================================================
-- pay_db – Dữ liệu mẫu (payment_methods, payments, transactions, customer_payment_methods)
-- Bảng do Django tạo: payment_methods, payments, transactions, customer_payment_methods
-- Chạy: psql -U postgres -d pay_db -f 07_pay_db_seed.sql
-- ============================================================

TRUNCATE transactions, customer_payment_methods, payments, payment_methods RESTART IDENTITY CASCADE;

INSERT INTO payment_methods (id, method_name, description, is_active) VALUES
(1, 'Tiền mặt', 'Thanh toán khi nhận hàng', true),
(2, 'Chuyển khoản', 'Chuyển khoản ngân hàng', true),
(3, 'Ví điện tử', 'MoMo, ZaloPay, VNPay', true);

INSERT INTO payments (id, order_id, payment_date, payment_amount, payment_method_id, payment_status, transaction_ref, admin_id) VALUES
(1, 1, NOW(), 150800, 2, 'completed', 'TXN001', 1),
(2, 2, NOW(), 83000, 2, 'completed', 'TXN002', NULL);

INSERT INTO transactions (id, order_id, refund_id, created_name, created_date, transaction_type, value, status) VALUES
(1, 1, NULL, '', NOW(), 'payment', 150800, 'success'),
(2, 2, NULL, '', NOW(), 'payment', 83000, 'success');

INSERT INTO customer_payment_methods (id, customer_id, payment_method_id, account_number, is_default, is_active) VALUES
(1, 1, 2, '***1234', true, true),
(2, 2, 2, '***1234', false, true);

SELECT setval(pg_get_serial_sequence('payment_methods', 'id'), 3);
SELECT setval(pg_get_serial_sequence('payments', 'id'), 2);
SELECT setval(pg_get_serial_sequence('transactions', 'id'), 2);
SELECT setval(pg_get_serial_sequence('customer_payment_methods', 'id'), 2);
