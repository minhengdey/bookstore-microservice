#!/bin/sh
# Helpers: auto mock seed khi docker compose up (source từ entrypoint.sh).

wait_for_product_catalog() {
    min_count="${1:-${MOCK_PRODUCT_COUNT:-50}}"
    if [ -f /app/common/docker/wait-for-product-catalog.py ]; then
        MOCK_PRODUCT_MIN="$min_count" python /app/common/docker/wait-for-product-catalog.py || return 1
    fi
    return 0
}

run_product_seed() {
    count="${MOCK_PRODUCT_COUNT:-320}"
    if [ "$MOCK_RESEED" = "true" ]; then
        echo "[mock-seed] Product: clear + reseed ($count items)..."
        python manage.py seed_mock --clear --force --count "$count" || true
    else
        echo "[mock-seed] Product: ensure catalog ($count items)..."
        python manage.py seed_mock --count "$count" || true
    fi
}

run_dependent_seed() {
    if [ "$MOCK_RESEED" = "true" ]; then
        python manage.py seed_mock --clear --force || true
    else
        python manage.py seed_mock || true
    fi
}

sync_product_flash_sales() {
    echo "[mock-seed] Syncing flash sales from promotion-service..."
    i=1
    while [ "$i" -le 10 ]; do
        if python manage.py sync_flash_sales; then
            return 0
        fi
        echo "[mock-seed] Flash sale sync retry $i/10..."
        sleep 4
        i=$((i + 1))
    done
    return 1
}
