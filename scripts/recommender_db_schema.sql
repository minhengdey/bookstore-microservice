-- ============================================================
-- recommender_db schema – recommender-ai-service
-- Tables: recommendations, customer_behaviors
-- ============================================================

\c recommender_db;

CREATE TABLE IF NOT EXISTS recommendations (
    id                  BIGSERIAL   PRIMARY KEY,
    customer_id         INTEGER     NOT NULL,
    book_id             INTEGER     NOT NULL,
    score               FLOAT       NOT NULL DEFAULT 0.0,
    recommendation_type VARCHAR(50) NOT NULL DEFAULT 'collaborative'
                          CHECK (recommendation_type IN
                                 ('collaborative','content_based','trending','personalized')),
    created_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, book_id)
);

CREATE TABLE IF NOT EXISTS customer_behaviors (
    id            BIGSERIAL    PRIMARY KEY,
    customer_id   INTEGER      NOT NULL,
    book_id       INTEGER      NOT NULL,
    action        VARCHAR(50)  NOT NULL
                    CHECK (action IN ('view','purchase','wishlist','cart_add','review')),
    action_weight FLOAT        NOT NULL DEFAULT 1.0,
    event_time    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendations_customer ON recommendations(customer_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_score    ON recommendations(score DESC);
CREATE INDEX IF NOT EXISTS idx_behaviors_customer       ON customer_behaviors(customer_id);
CREATE INDEX IF NOT EXISTS idx_behaviors_book           ON customer_behaviors(book_id);
