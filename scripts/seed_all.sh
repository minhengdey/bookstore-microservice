#!/bin/sh
# Chạy seed mock data cho tất cả microservices (theo thứ tự phụ thuộc).
# Yêu cầu: Docker Compose đang chạy (docker compose up -d).
# Cách chạy: ./scripts/seed_all.sh   hoặc   sh scripts/seed_all.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SERVICES="auth-service user-service product-service cart-service order-service payment-service shipping-service recommender-ai-service"

echo "=== Seed mock data (root: $ROOT) ==="

for svc in $SERVICES; do
  echo ""
  echo "[$svc] Running seed_mock..."
  docker compose exec -T "$svc" python manage.py seed_mock
  echo "[$svc] OK"
  # After seeding, ensure serial sequences are aligned to avoid id collisions
  case "$svc" in
    auth-service)
      echo "[auth-service] Fixing sequence for auth_users..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 5433 -U postgres -d auth_db -c "SELECT setval(pg_get_serial_sequence('auth_users','id'), COALESCE((SELECT MAX(id) FROM auth_users),1));"
      ;;
    user-service)
      echo "[user-service] Fixing sequence for users..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55437 -U postgres -d user_db -c "SELECT setval(pg_get_serial_sequence('users','id'), COALESCE((SELECT MAX(id) FROM users),1));"
      ;;
    product-service)
      echo "[product-service] Fixing sequence for products..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55432 -U postgres -d product_db -c "SELECT setval(pg_get_serial_sequence('products','id'), COALESCE((SELECT MAX(id) FROM products),1));"
      ;;
    order-service)
      echo "[order-service] Fixing sequence for orders..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55434 -U postgres -d order_db -c "SELECT setval(pg_get_serial_sequence('orders','id'), COALESCE((SELECT MAX(id) FROM orders),1));"
      ;;
    payment-service)
      echo "[payment-service] Fixing sequence for payments..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55435 -U postgres -d pay_db -c "SELECT setval(pg_get_serial_sequence('payments','id'), COALESCE((SELECT MAX(id) FROM payments),1));"
      ;;
    shipping-service)
      echo "[shipping-service] Fixing sequence for shippings..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55436 -U postgres -d ship_db -c "SELECT setval(pg_get_serial_sequence('shippings','id'), COALESCE((SELECT MAX(id) FROM shippings),1));"
      ;;
    recommender-ai-service)
      echo "[recommender-ai-service] Fixing sequence for recommender (if applicable)..."
      docker run --rm -e PGPASSWORD=${PGPASSWORD:-minhanh2722004} postgres:15-alpine \
        psql -h host.docker.internal -p 55438 -U postgres -d recommender_db -c "SELECT setval(pg_get_serial_sequence('recommender_table','id'), COALESCE((SELECT MAX(id) FROM recommender_table),1));" || true
      ;;
  esac
done

echo ""
echo "=== Hoàn thành seed tất cả services ==="
