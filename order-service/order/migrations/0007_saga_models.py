"""Create UUID saga tables used by OrderSagaManager (separate from legacy orders table)."""

from django.db import migrations


CREATE_SAGA_TABLES = """
CREATE TABLE IF NOT EXISTS order_order (
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    id uuid NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL,
    correlation_id uuid NOT NULL,
    status varchar(30) NOT NULL DEFAULT 'DRAFT',
    total_amount numeric(12, 2) NOT NULL,
    promotion_id uuid NULL,
    promotion_code varchar(50) NULL,
    discount_amount numeric(12, 2) NOT NULL DEFAULT 0,
    final_amount numeric(12, 2) NOT NULL,
    payment_id uuid NULL,
    payment_provider varchar(50) NULL,
    shipping_address jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS order_orderitem (
    id uuid NOT NULL PRIMARY KEY,
    product_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    quantity integer NOT NULL CHECK (quantity >= 0),
    unit_price numeric(12, 2) NOT NULL,
    product_name varchar(255) NOT NULL,
    variant_sku varchar(100) NOT NULL,
    variant_attributes jsonb NOT NULL DEFAULT '{}',
    order_id uuid NOT NULL REFERENCES order_order(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS order_ordersaga (
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    id uuid NOT NULL PRIMARY KEY,
    correlation_id uuid NOT NULL,
    current_step varchar(50) NOT NULL,
    status varchar(20) NOT NULL,
    last_error text NULL,
    retry_count integer NOT NULL DEFAULT 0,
    timeout_at timestamptz NULL,
    order_id uuid NOT NULL UNIQUE REFERENCES order_order(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS order_orderstatushistory (
    id uuid NOT NULL PRIMARY KEY,
    status varchar(30) NOT NULL,
    reason text NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    order_id uuid NOT NULL REFERENCES order_order(id) DEFERRABLE INITIALLY DEFERRED
);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0006_orderitem_variant_fields"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SAGA_TABLES, migrations.RunSQL.noop),
    ]
