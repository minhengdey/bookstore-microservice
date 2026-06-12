#!/bin/sh

echo "Waiting for PostgreSQL..."
while ! python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('inventory-db', 5432))" 2>/dev/null; do
  sleep 0.1
done
echo "PostgreSQL started"

if [ -z "$SKIP_MIGRATE" ]; then
  echo "Running migrations..."
  python manage.py makemigrations inventory --noinput || true
  python manage.py migrate --noinput
else
  . /app/common/docker/wait-for-tables.sh
fi

if [ $# -eq 0 ]; then
  echo "Starting server..."
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "Executing command: $@"
  exec "$@"
fi
