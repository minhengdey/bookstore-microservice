import logging
import os
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from promotion.models import FlashSale, FlashSaleItem, Voucher

logger = logging.getLogger(__name__)
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")

# Fallback khi không gọi được product-service (product_id, discount_price, quantity)
FALLBACK_FLASH_ITEMS = [
    {"product_id": 1, "discount_price": Decimal("1590000"), "quantity": 50},
    {"product_id": 2, "discount_price": Decimal("1990000"), "quantity": 30},
    {"product_id": 3, "discount_price": Decimal("1290000"), "quantity": 40},
    {"product_id": 4, "discount_price": Decimal("3990000"), "quantity": 25},
    {"product_id": 5, "discount_price": Decimal("5490000"), "quantity": 20},
    {"product_id": 6, "discount_price": Decimal("2190000"), "quantity": 35},
    {"product_id": 7, "discount_price": Decimal("2590000"), "quantity": 30},
    {"product_id": 8, "discount_price": Decimal("1190000"), "quantity": 40},
    {"product_id": 9, "discount_price": Decimal("690000"), "quantity": 60},
    {"product_id": 10, "discount_price": Decimal("1090000"), "quantity": 45},
    {"product_id": 11, "discount_price": Decimal("350000"), "quantity": 80},
    {"product_id": 12, "discount_price": Decimal("199000"), "quantity": 100},
]


def _round_vnd(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("1000"), rounding=ROUND_HALF_UP)


def _discount_price(list_price, pct: int = 20) -> Decimal:
    price = Decimal(str(list_price))
    return _round_vnd(price * Decimal(100 - pct) / Decimal(100))


def _fetch_products(max_items=320):
    products = []
    page = 1
    page_size = 200
    try:
        while len(products) < max_items:
            r = requests.get(
                f"{PRODUCT_SERVICE_URL}/products/",
                params={"page": page, "page_size": page_size},
                timeout=12,
            )
            if r.status_code != 200:
                break
            payload = r.json()
            if isinstance(payload, list):
                batch = payload
                total_pages = 1
            else:
                batch = payload.get("results") or []
                total_pages = int(payload.get("total_pages") or 1)
            if not batch:
                break
            products.extend(batch)
            if page >= total_pages:
                break
            page += 1
        return products[:max_items]
    except Exception as exc:
        logger.warning("Cannot fetch products for flash sale seed: %s", exc)
        return products[:max_items]


def _build_flash_items_from_products(products, limit=40, discount_pct=20):
    items = []
    for product in products[:limit]:
        product_id = product.get("id")
        list_price = product.get("price") or product.get("list_price")
        if not product_id or list_price is None:
            continue
        items.append({
            "product_id": product_id,
            "discount_price": _discount_price(list_price, discount_pct),
            "quantity": max(20, min(100, int(product.get("stock") or 50) // 2)),
        })
    return items


class Command(BaseCommand):
    help = "Seed vouchers and flash sales for development/demo"

    def handle(self, *args, **options):
        now = timezone.now()
        vouchers = [
            {
                "code": "WELCOME10",
                "discount_percentage": Decimal("10"),
                "min_order_value": Decimal("500000"),
                "max_discount_amount": Decimal("500000"),
                "usage_limit": 1000,
            },
            {
                "code": "SAVE50K",
                "discount_amount": Decimal("50000"),
                "min_order_value": Decimal("300000"),
                "usage_limit": 500,
            },
            {
                "code": "VIP15",
                "discount_percentage": Decimal("15"),
                "min_order_value": Decimal("1000000"),
                "max_discount_amount": Decimal("1000000"),
                "usage_limit": 200,
            },
        ]
        for data in vouchers:
            obj, created = Voucher.objects.get_or_create(
                code=data["code"],
                defaults={
                    **data,
                    "start_date": now - timedelta(days=1),
                    "end_date": now + timedelta(days=90),
                    "is_active": True,
                    "used_count": 0,
                },
            )
            if not created:
                for key, value in data.items():
                    setattr(obj, key, value)
                obj.start_date = now - timedelta(days=1)
                obj.end_date = now + timedelta(days=90)
                obj.is_active = True
                obj.save()

        flash_limit = int(os.environ.get("MOCK_FLASH_SALE_COUNT", "40"))
        products = _fetch_products(max_items=int(os.environ.get("MOCK_PRODUCT_COUNT", "320")))
        flash_items = _build_flash_items_from_products(products, limit=flash_limit) if products else FALLBACK_FLASH_ITEMS
        if not flash_items:
            flash_items = FALLBACK_FLASH_ITEMS

        flash_sale, _ = FlashSale.objects.update_or_create(
            name="Siêu Sale Giữa Tháng",
            defaults={
                "start_date": now - timedelta(days=1),
                "end_date": now + timedelta(days=14),
                "is_active": True,
            },
        )

        seeded_ids = set()
        for item in flash_items:
            product_id = item["product_id"]
            seeded_ids.add(product_id)
            obj, created = FlashSaleItem.objects.get_or_create(
                flash_sale=flash_sale,
                product_id=product_id,
                defaults={
                    "discount_price": item["discount_price"],
                    "quantity": item["quantity"],
                    "sold_count": 0,
                },
            )
            if not created:
                obj.discount_price = item["discount_price"]
                obj.quantity = item["quantity"]
                obj.save(update_fields=["discount_price", "quantity"])
            action = "created" if created else "updated"
            self.stdout.write(f"  Flash item product #{product_id}: {action}")

        # Gỡ sản phẩm không còn trong đợt sale này
        removed = (
            FlashSaleItem.objects.filter(flash_sale=flash_sale)
            .exclude(product_id__in=seeded_ids)
            .delete()[0]
        )
        if removed:
            self.stdout.write(self.style.WARNING(f"  Removed {removed} stale flash sale item(s)."))

        self.stdout.write(self.style.SUCCESS(
            f"Flash sale '{flash_sale.name}' has {len(seeded_ids)} product(s)."
        ))

        synced = self._sync_products()
        if synced:
            self.stdout.write(self.style.SUCCESS(f"Product flash sale sync: {synced}"))

        self.stdout.write(self.style.SUCCESS("Promotion seed data ready."))

    def _sync_products(self):
        try:
            from common.client import InternalClient

            client = InternalClient()
            r = client.post(f"{PRODUCT_SERVICE_URL}/internal/sync-flash-sales/", json={})
            if r.status_code == 200:
                return r.json()
            logger.warning("Product flash sale sync failed: HTTP %s", r.status_code)
        except Exception as exc:
            logger.warning("InternalClient sync skipped: %s", exc)

        try:
            r = requests.post(
                f"{PRODUCT_SERVICE_URL}/internal/sync-flash-sales/",
                json={},
                headers={"X-Internal-Token": os.environ.get("INTERNAL_TOKEN", "internal-dev-token")},
                timeout=10,
            )
            if r.status_code == 200:
                return r.json()
            logger.warning("Product flash sale sync fallback failed: HTTP %s", r.status_code)
        except Exception as exc:
            logger.warning("Product flash sale sync fallback skipped: %s", exc)
        return None
