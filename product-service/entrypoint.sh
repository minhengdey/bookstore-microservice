#!/bin/sh

echo "Waiting for database..."
sleep 2

echo "[entrypoint] Installing common package..."
if [ -d /app/common ]; then
    pip install -q -e /app/common || true
fi

if [ -f /app/common/docker/mock-seed-common.sh ]; then
    . /app/common/docker/mock-seed-common.sh
fi

echo "Applying migrations..."
python manage.py makemigrations product --noinput
python manage.py migrate --noinput

run_product_seed
sync_product_flash_sales || true

if [ $# -eq 0 ]; then
  echo "Starting server..."
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "Executing command: $@"
  exec "$@"
fi
