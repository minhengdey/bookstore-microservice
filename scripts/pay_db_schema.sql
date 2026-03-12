-- ============================================================
-- pay_db schema – pay-service
-- Tables: payments
-- ============================================================

\c pay_db;

CREATE TABLE IF NOT EXISTS payments (
    id               BIGSERIAL      PRIMARY KEY,
    order_id         INTEGER        NOT NULL UNIQUE,
    customer_id      INTEGER        NOT NULL,
    amount           NUMERIC(12, 2) NOT NULL,
    payment_method   VARCHAR(50)    NOT NULL
                       CHECK (payment_method IN ('credit_card','debit_card',
                                                  'bank_transfer','e_wallet','cash_on_delivery')),
    status           VARCHAR(30)    NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','processing','completed','failed','refunded')),
    transaction_id   VARCHAR(255)   NOT NULL DEFAULT '',
    payment_date     TIMESTAMPTZ,
    created_date     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_order    ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_status   ON payments(status);
