-- ============================================================
-- staff_db schema – staff-service
-- Tables: staff_users, staffs
-- ============================================================

\c staff_db;

CREATE TABLE IF NOT EXISTS staff_users (
    id           BIGSERIAL    PRIMARY KEY,
    username     VARCHAR(150) NOT NULL UNIQUE,
    email        VARCHAR(254) NOT NULL UNIQUE,
    password     VARCHAR(255) NOT NULL,
    phone        VARCHAR(20)  NOT NULL DEFAULT '',
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_date TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staffs (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      BIGINT       NOT NULL UNIQUE REFERENCES staff_users(id) ON DELETE CASCADE,
    department   VARCHAR(100) NOT NULL DEFAULT '',
    position     VARCHAR(100) NOT NULL DEFAULT '',
    hire_date    DATE,
    salary       NUMERIC(12, 2) NOT NULL DEFAULT 0
);
