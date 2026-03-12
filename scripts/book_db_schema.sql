-- ============================================================
-- book_db schema – book-service
-- Tables: books, book_images, book_authors, book_categories,
--         book_genres, book_publishers, book_conditions, book_languages
-- ============================================================

\c book_db;

CREATE TABLE IF NOT EXISTS books (
    id               BIGSERIAL       PRIMARY KEY,
    title            VARCHAR(500)    NOT NULL,
    isbn             VARCHAR(20)     NOT NULL DEFAULT '' UNIQUE,
    description      TEXT            NOT NULL DEFAULT '',
    publication_year INTEGER,
    page_count       INTEGER,
    list_price       NUMERIC(10, 2)  NOT NULL,
    sale_price       NUMERIC(10, 2)  NOT NULL,
    stock            INTEGER         NOT NULL DEFAULT 0,
    status           VARCHAR(20)     NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active','inactive','out_of_stock')),
    created_date     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_date     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS book_images (
    id         BIGSERIAL      PRIMARY KEY,
    book_id    BIGINT         NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    image_url  VARCHAR(1000)  NOT NULL,
    is_primary BOOLEAN        NOT NULL DEFAULT FALSE
);

-- Cross-service references stored as plain integers (no FK across DB boundaries)
CREATE TABLE IF NOT EXISTS book_authors (
    id        BIGSERIAL PRIMARY KEY,
    book_id   BIGINT    NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    author_id INTEGER   NOT NULL,
    UNIQUE (book_id, author_id)
);

CREATE TABLE IF NOT EXISTS book_categories (
    id          BIGSERIAL PRIMARY KEY,
    book_id     BIGINT    NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    category_id INTEGER   NOT NULL,
    UNIQUE (book_id, category_id)
);

CREATE TABLE IF NOT EXISTS book_genres (
    id       BIGSERIAL PRIMARY KEY,
    book_id  BIGINT    NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    genre_id INTEGER   NOT NULL,
    UNIQUE (book_id, genre_id)
);

CREATE TABLE IF NOT EXISTS book_publishers (
    id           BIGSERIAL PRIMARY KEY,
    book_id      BIGINT    NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    publisher_id INTEGER   NOT NULL,
    UNIQUE (book_id, publisher_id)
);

CREATE TABLE IF NOT EXISTS book_conditions (
    id             BIGSERIAL      PRIMARY KEY,
    book_id        BIGINT         NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    format         VARCHAR(100)   NOT NULL,
    format_price   NUMERIC(10, 2) NOT NULL,
    book_condition VARCHAR(100)   NOT NULL
);

CREATE TABLE IF NOT EXISTS book_languages (
    id            BIGSERIAL    PRIMARY KEY,
    book_id       BIGINT       NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    language_name VARCHAR(100) NOT NULL,
    UNIQUE (book_id, language_name)
);

CREATE INDEX IF NOT EXISTS idx_books_status  ON books(status);
CREATE INDEX IF NOT EXISTS idx_books_title   ON books USING GIN (to_tsvector('english', title));
