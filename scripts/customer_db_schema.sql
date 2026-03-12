-- ============================================================
-- customer_db schema – customer-service
-- Tables: users, customers, web_addresses
-- ============================================================

\c customer_db;

CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL    PRIMARY KEY,
    username    VARCHAR(150) NOT NULL UNIQUE,
    email       VARCHAR(254) NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    phone       VARCHAR(20)  NOT NULL DEFAULT '',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id             BIGSERIAL   PRIMARY KEY,
    user_id        BIGINT      NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    loyalty_points INTEGER     NOT NULL DEFAULT 0,
    created_date   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS web_addresses (
    id              BIGSERIAL    PRIMARY KEY,
    customer_id     BIGINT       NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    recipient_name  VARCHAR(255) NOT NULL,
    address_line    VARCHAR(500) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(100) NOT NULL DEFAULT '',
    country         VARCHAR(100) NOT NULL,
    postal_code     VARCHAR(20)  NOT NULL,
    phone           VARCHAR(20)  NOT NULL DEFAULT '',
    is_default      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_web_addresses_customer ON web_addresses(customer_id);
