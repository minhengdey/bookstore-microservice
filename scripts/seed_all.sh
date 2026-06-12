#!/bin/sh
# Seed mock data lớn cho toàn bộ microservices (theo thứ tự phụ thuộc).
# Lưu ý: docker compose up đã tự seed qua entrypoint — script này dùng khi muốn seed lại thủ công.
#
# Cách dùng:
#   ./scripts/seed_all.sh
#   ./scripts/seed_all.sh --clear          # xóa và seed lại toàn bộ
#   MOCK_PRODUCT_COUNT=400 ./scripts/seed_all.sh --clear

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CLEAR_FLAG=""
FORCE_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --clear) CLEAR_FLAG="--clear" ;;
    --force) FORCE_FLAG="--force" ;;
  esac
done

if [ -n "$CLEAR_FLAG" ]; then
  FORCE_FLAG="--force"
fi

PRODUCT_COUNT="${MOCK_PRODUCT_COUNT:-320}"
CUSTOMER_COUNT="${MOCK_CUSTOMER_COUNT:-50}"
SEED_ARGS="$CLEAR_FLAG $FORCE_FLAG --count $PRODUCT_COUNT"

echo "=== Seed mock data (products=$PRODUCT_COUNT, customers=$CUSTOMER_COUNT) ==="

echo ""
echo "[auth-service] bootstrap_default_users..."
docker compose exec -T -e MOCK_CUSTOMER_COUNT="$CUSTOMER_COUNT" auth-service \
  python manage.py bootstrap_default_users --no-input
echo "[auth-service] OK"

echo ""
echo "[user-service] seed_rbac..."
docker compose exec -T user-service python manage.py seed_rbac
echo "[user-service] OK"

echo ""
echo "[product-service] seed_mock $SEED_ARGS..."
docker compose exec -T -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" product-service \
  python manage.py seed_mock $SEED_ARGS
echo "[product-service] OK"

echo ""
echo "[promotion-service] seed_promotions..."
docker compose exec -T \
  -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" \
  -e MOCK_FLASH_SALE_COUNT="${MOCK_FLASH_SALE_COUNT:-40}" \
  promotion-service python manage.py seed_promotions
echo "[promotion-service] OK"

echo ""
echo "[product-service] sync_flash_sales..."
docker compose exec -T product-service python manage.py sync_flash_sales || true
echo "[product-service] flash sync OK"

echo ""
echo "[cart-service] seed_mock..."
docker compose exec -T \
  -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" \
  -e MOCK_CUSTOMER_COUNT="$CUSTOMER_COUNT" \
  cart-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[cart-service] OK"

echo ""
echo "[order-service] seed_mock..."
docker compose exec -T \
  -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" \
  -e MOCK_CUSTOMER_COUNT="$CUSTOMER_COUNT" \
  order-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[order-service] OK"

echo ""
echo "[payment-service] seed_mock..."
docker compose exec -T payment-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[payment-service] OK"

echo ""
echo "[shipping-service] seed_mock..."
docker compose exec -T shipping-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[shipping-service] OK"

echo ""
echo "[interaction-service] seed_mock..."
docker compose exec -T \
  -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" \
  -e MOCK_CUSTOMER_COUNT="$CUSTOMER_COUNT" \
  interaction-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[interaction-service] OK"

echo ""
echo "[recommender-ai-service] seed_mock..."
docker compose exec -T \
  -e MOCK_PRODUCT_COUNT="$PRODUCT_COUNT" \
  -e MOCK_CUSTOMER_COUNT="$CUSTOMER_COUNT" \
  recommender-ai-service python manage.py seed_mock $CLEAR_FLAG $FORCE_FLAG
echo "[recommender-ai-service] OK"

echo ""
echo "[recommender-ai-service] build_catalog_index --force..."
docker compose exec -T recommender-ai-service python manage.py build_catalog_index --force
echo "[recommender-ai-service] catalog index OK"

echo ""
echo "=== Hoàn thành seed toàn bộ hệ thống ==="
echo "Gợi ý: đăng nhập customer1..customer${CUSTOMER_COUNT} / password123"
