#!/bin/sh
# API Gateway: không dùng PostgreSQL, chỉ chạy Django (proxy + web)
echo "[entrypoint] Starting API Gateway with Gunicorn..."
# Use environment variables to tune workers/threads in different environments
WORKERS=${GUNICORN_WORKERS:-4}
THREADS=${GUNICORN_THREADS:-4}
KEEP_ALIVE=${GUNICORN_KEEP_ALIVE:-5}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
exec gunicorn api_gateway.wsgi:application \
	--bind 0.0.0.0:8000 \
	--workers ${WORKERS} \
	--threads ${THREADS} \
	--keep-alive ${KEEP_ALIVE} \
	--timeout ${TIMEOUT}
