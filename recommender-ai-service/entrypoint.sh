#!/bin/sh
echo "[entrypoint] Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.environ.get('DB_HOST','host.docker.internal'),
        port=int(os.environ.get('DB_PORT','5432')),
        user=os.environ.get('DB_USER','postgres'),
        password=os.environ.get('DB_PASSWORD','postgres'),
        dbname=os.environ.get('DB_NAME','postgres'),
    ).close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null
do
    echo "[entrypoint] PostgreSQL not ready - retrying in 2s..."
    sleep 2
done
echo "[entrypoint] PostgreSQL is ready!"

echo "[entrypoint] Installing common package..."
pip install -q "protobuf>=3.20.3,<5.0.0" || true
if [ -d /app/common ]; then
    pip install -q -e /app/common || true
    pip install -q "protobuf>=3.20.3,<5.0.0" || true
fi

if [ -f /app/common/docker/mock-seed-common.sh ]; then
    . /app/common/docker/mock-seed-common.sh
fi

if [ "$#" -eq 0 ]; then
    python manage.py makemigrations app --noinput || true
    python manage.py migrate --no-input

    wait_for_product_catalog "${MOCK_PRODUCT_COUNT:-320}" || true
    run_dependent_seed
    python manage.py sync_purchase_behaviors || true
    python manage.py sync_interaction_behaviors || true
    python manage.py ensure_recommender_models || true
    python manage.py build_catalog_index || true

    echo "[entrypoint] Starting cron and adding django crontab..."
    service cron start
    python manage.py crontab add

    exec python manage.py runserver 0.0.0.0:8000 --noreload
else
    if [ -n "$SKIP_MIGRATE" ]; then
        . /app/common/docker/wait-for-tables.sh
    fi
    echo "[entrypoint] Running command: $@"
    exec "$@"
fi
