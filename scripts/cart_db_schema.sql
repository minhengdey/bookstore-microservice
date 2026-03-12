-- ============================================================
-- cart_db schema – cart-service
-- Tables: carts, cart_items
-- ============================================================

\c cart_db;

CREATE TABLE IF NOT EXISTS carts (
    id          BIGSERIAL   PRIMARY KEY,
    customer_id INTEGER     NOT NULL UNIQUE,
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cart_items (
    id         BIGSERIAL      PRIMARY KEY,
    cart_id    BIGINT         NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    book_id    INTEGER        NOT NULL,
    quantity   INTEGER        NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    UNIQUE (cart_id, book_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);
