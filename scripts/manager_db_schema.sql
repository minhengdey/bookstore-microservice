-- ============================================================
-- manager_db schema – manager-service
-- Tables: manager_users, managers
-- ============================================================

\c manager_db;

CREATE TABLE IF NOT EXISTS manager_users (
    id           BIGSERIAL    PRIMARY KEY,
    username     VARCHAR(150) NOT NULL UNIQUE,
    email        VARCHAR(254) NOT NULL UNIQUE,
    password     VARCHAR(255) NOT NULL,
    phone        VARCHAR(20)  NOT NULL DEFAULT '',
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_date TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS managers (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      BIGINT       NOT NULL UNIQUE REFERENCES manager_users(id) ON DELETE CASCADE,
    access_level INTEGER      NOT NULL DEFAULT 1 CHECK (access_level BETWEEN 1 AND 5)
);
