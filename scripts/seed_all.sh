#!/bin/sh
# Chạy seed mock data cho tất cả microservices (theo thứ tự phụ thuộc).
# Yêu cầu: Docker Compose đang chạy (docker compose up -d).
# Cách chạy: ./scripts/seed_all.sh   hoặc   sh scripts/seed_all.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SERVICES="customer-service catalog-service book-service staff-service cart-service order-service pay-service ship-service manager-service comment-rate-service recommender-ai-service"

echo "=== Seed mock data (root: $ROOT) ==="

for svc in $SERVICES; do
  echo ""
  echo "[$svc] Running seed_mock..."
  docker compose exec -T "$svc" python manage.py seed_mock
  echo "[$svc] OK"
done

echo ""
echo "=== Hoàn thành seed tất cả services ==="
