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
if [ -d /app/common ]; then
    pip install -q -e /app/common || true
fi

if [ "$#" -eq 0 ]; then
    python manage.py makemigrations app --no-input
    python manage.py migrate --no-input
    python manage.py seed_mock || true

    echo "[entrypoint] Starting cron and adding django crontab..."
    service cron start
    python manage.py crontab add

    exec python manage.py runserver 0.0.0.0:8000 --noreload
else
    echo "[entrypoint] Running command: $@"
    exec "$@"
fi