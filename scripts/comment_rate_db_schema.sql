-- ============================================================
-- comment_rate_db schema – comment-rate-service
-- Tables: reviews, review_likes
-- ============================================================

\c comment_rate_db;

CREATE TABLE IF NOT EXISTS reviews (
    id           BIGSERIAL    PRIMARY KEY,
    book_id      INTEGER      NOT NULL,
    customer_id  INTEGER      NOT NULL,
    rating       SMALLINT     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment      TEXT         NOT NULL DEFAULT '',
    is_approved  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_date TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (book_id, customer_id)
);

CREATE TABLE IF NOT EXISTS review_likes (
    id           BIGSERIAL   PRIMARY KEY,
    review_id    BIGINT      NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    customer_id  INTEGER     NOT NULL,
    UNIQUE (review_id, customer_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_book     ON reviews(book_id);
CREATE INDEX IF NOT EXISTS idx_reviews_customer ON reviews(customer_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating   ON reviews(rating);
