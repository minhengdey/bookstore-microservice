#!/bin/sh

# Chờ database (nếu cần, nhưng ở đây kết nối trực tiếp host nên thường OK ngay)
echo "Waiting for database..."
sleep 2

echo "[entrypoint] Installing common package..."
if [ -d /app/common ]; then
    pip install -q -e /app/common || true
fi

echo "Applying migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Starting server..."
python manage.py runserver 0.0.0.0:8000
