-- ============================================================
-- catalog_db schema – catalog-service
-- Tables: authors, categories, genres, publishers
-- ============================================================

\c catalog_db;

CREATE TABLE IF NOT EXISTS authors (
    id          BIGSERIAL    PRIMARY KEY,
    author_name VARCHAR(255) NOT NULL,
    biography   TEXT         NOT NULL DEFAULT '',
    birth_year  INTEGER,
    death_year  INTEGER
);

CREATE TABLE IF NOT EXISTS categories (
    id                 BIGSERIAL    PRIMARY KEY,
    category_name      VARCHAR(255) NOT NULL,
    parent_category_id BIGINT       REFERENCES categories(id) ON DELETE SET NULL,
    description        TEXT         NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS genres (
    id          BIGSERIAL    PRIMARY KEY,
    genre_name  VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS publishers (
    id               BIGSERIAL    PRIMARY KEY,
    publisher_name   VARCHAR(255) NOT NULL,
    contact_name     VARCHAR(255) NOT NULL DEFAULT '',
    address          TEXT         NOT NULL DEFAULT '',
    phone            VARCHAR(20)  NOT NULL DEFAULT '',
    website          VARCHAR(500) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_category_id);
