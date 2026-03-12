-- ============================================================
-- order_db schema – order-service
-- Tables: orders, order_items
-- ============================================================

\c order_db;

CREATE TABLE IF NOT EXISTS orders (
    id             BIGSERIAL      PRIMARY KEY,
    customer_id    INTEGER        NOT NULL,
    status         VARCHAR(30)    NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','confirmed','processing',
                                       'shipped','delivered','cancelled')),
    total_amount   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    shipping_address TEXT         NOT NULL DEFAULT '',
    notes          TEXT           NOT NULL DEFAULT '',
    created_date   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_date   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id         BIGSERIAL      PRIMARY KEY,
    order_id   BIGINT         NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    book_id    INTEGER        NOT NULL,
    quantity   INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    UNIQUE (order_id, book_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(status);
