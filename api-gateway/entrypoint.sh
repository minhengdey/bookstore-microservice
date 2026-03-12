#!/bin/sh
# API Gateway: không dùng PostgreSQL, chỉ chạy Django (proxy + web)
echo "[entrypoint] Starting API Gateway..."
exec python manage.py runserver 0.0.0.0:8000
