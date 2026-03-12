-- ============================================================
-- ship_db schema – ship-service
-- Tables: shipments, shipment_trackings
-- ============================================================

\c ship_db;

CREATE TABLE IF NOT EXISTS shipments (
    id               BIGSERIAL    PRIMARY KEY,
    order_id         INTEGER      NOT NULL UNIQUE,
    customer_id      INTEGER      NOT NULL,
    carrier          VARCHAR(100) NOT NULL DEFAULT '',
    tracking_number  VARCHAR(255) NOT NULL DEFAULT '',
    status           VARCHAR(30)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','picked_up','in_transit',
                                         'out_for_delivery','delivered','failed')),
    shipping_address TEXT         NOT NULL,
    estimated_date   DATE,
    delivered_date   TIMESTAMPTZ,
    created_date     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shipment_trackings (
    id          BIGSERIAL    PRIMARY KEY,
    shipment_id BIGINT       NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    location    VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    event_time  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_order    ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON shipments(tracking_number);
