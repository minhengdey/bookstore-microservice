from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import redis
import json
import os
import logging
from common.client import InternalClient
from .models import Product, Category, Brand, ProductVariant

logger = logging.getLogger(__name__)
PROMOTION_SERVICE_URL = os.environ.get("PROMOTION_SERVICE_URL", "http://promotion-service:8000")

redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

def invalidate_product_cache(product_id=None):
    try:
        if product_id:
            redis_client.delete(f"product:{product_id}")
        redis_client.incr("product_list_version")
    except Exception as e:
        # Ignore cache invalidation failures if Redis is down
        pass

class CategoryService:
    def list(self): return Category.objects.all()
    def get(self, pk):
        c = Category.objects.filter(pk=pk).first()
        if not c: raise ValueError(f"Category {pk} not found")
        return c
    def create(self, data): return Category.objects.create(**data)
    def update(self, pk, data):
        c = self.get(pk)
        for k, v in data.items():
            setattr(c, k, v)
        c.save()
        return c

class BrandService:
    def list(self): return Brand.objects.all()
    def get(self, pk):
        b = Brand.objects.filter(pk=pk).first()
        if not b: raise ValueError(f"Brand {pk} not found")
        return b
    def create(self, data): return Brand.objects.create(**data)
    def update(self, pk, data):
        b = self.get(pk)
        for k, v in data.items():
            setattr(b, k, v)
        b.save()
        return b

class ProductVariantService:
    def get(self, pk):
        v = ProductVariant.objects.filter(pk=pk).first()
        if not v: raise ValueError(f"Variant {pk} not found")
        return v
    def create(self, data):
        v = ProductVariant.objects.create(**data)
        invalidate_product_cache(v.product_id)
        return v
    def update(self, pk, data):
        v = self.get(pk)
        for k, val in data.items():
            setattr(v, k, val)
        v.save()
        invalidate_product_cache(v.product_id)
        return v
    def delete(self, pk):
        v = self.get(pk)
        p_id = v.product_id
        v.delete()
        invalidate_product_cache(p_id)


class ProductService:
    def list(self): return Product.objects.select_related("category", "brand").prefetch_related("variants").all()
    def get(self, pk):
        p = Product.objects.select_related("category", "brand").prefetch_related("variants").filter(pk=pk).first()

        if not p: raise ValueError(f"Product {pk} not found")
        p.refresh_flash_sale_state(save=True)
        return p

    def list_flash_sale(self):
        now = timezone.now()
        return self.list().filter(
            is_flash_sale=True,
            flash_sale_price__isnull=False,
            flash_sale_ends_at__gt=now,
        )

    def sync_flash_sales_from_promotion(self):
        client = InternalClient()
        try:
            r = client.get(
                f"{PROMOTION_SERVICE_URL}/api/promotions/flash-sales/",
                params={"active": "true"},
            )
        except Exception as e:
            logger.warning(f"Cannot reach promotion-service for flash sale sync: {e}")
            return {"synced": 0, "cleared": 0}

        if r.status_code != 200:
            logger.warning(f"Flash sale sync failed: HTTP {r.status_code}")
            return {"synced": 0, "cleared": 0}

        payload = r.json()
        sales = payload if isinstance(payload, list) else payload.get("results", [])
        active_product_ids = set()
        synced = 0

        with transaction.atomic():
            for sale in sales:
                sale_id = sale.get("id")
                sale_name = sale.get("name", "")
                ends_at = sale.get("end_date")
                for item in sale.get("items") or []:
                    product_id = item.get("product_id")
                    sale_price = item.get("discount_price")
                    if not product_id or sale_price is None:
                        continue
                    product = Product.objects.filter(pk=product_id).first()
                    if not product:
                        continue
                    remaining = int(item.get("quantity", 0)) - int(item.get("sold_count", 0))
                    if remaining <= 0:
                        continue
                    active_product_ids.add(product_id)
                    product.is_flash_sale = True
                    product.flash_sale_price = Decimal(str(sale_price))
                    product.flash_sale_name = sale_name
                    product.flash_sale_id = sale_id
                    if ends_at:
                        from django.utils.dateparse import parse_datetime
                        parsed = parse_datetime(str(ends_at))
                        if parsed and timezone.is_naive(parsed):
                            parsed = timezone.make_aware(parsed)
                        product.flash_sale_ends_at = parsed
                    product.save(update_fields=[
                        "is_flash_sale", "flash_sale_price", "flash_sale_name",
                        "flash_sale_id", "flash_sale_ends_at", "updated_at",
                    ])
                    invalidate_product_cache(product_id)
                    synced += 1

            cleared = 0
            stale_qs = Product.objects.filter(is_flash_sale=True)
            if active_product_ids:
                stale_qs = stale_qs.exclude(id__in=active_product_ids)
            for product in stale_qs:
                product.is_flash_sale = False
                product.flash_sale_price = None
                product.flash_sale_name = ""
                product.flash_sale_ends_at = None
                product.flash_sale_id = None
                product.save(update_fields=[
                    "is_flash_sale", "flash_sale_price", "flash_sale_name",
                    "flash_sale_ends_at", "flash_sale_id", "updated_at",
                ])
                invalidate_product_cache(product.id)
                cleared += 1

        invalidate_product_cache()
        return {"synced": synced, "cleared": cleared}

    def create(self, data):
        p = Product.objects.create(**data)
        invalidate_product_cache()
        return p

    def update(self, pk, data):
        p = self.get(pk)
        for k, v in data.items():
            setattr(p, k, v)
        p.save()
        invalidate_product_cache(pk)
        return p

    def reserve_stock(self, order_id: int, items: list):
        """
        items: [{"product_id": int, "quantity": int}]
        """
        # Sort items to prevent deadlocks
        items = sorted(items, key=lambda x: x["product_id"])
        
        with transaction.atomic():
            product_ids = [item["product_id"] for item in items]
            # Lock the rows using select_for_update
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            
            product_map = {p.id: p for p in products}
            
            # Validate all items
            for item in items:
                p_id = item["product_id"]
                qty = item["quantity"]
                if p_id not in product_map:
                    raise ValueError(f"Product {p_id} not found")
                
                product = product_map[p_id]
                if product.stock < qty:
                    raise ValueError(f"Insufficient stock for product {p_id}. Requested: {qty}, Available: {product.stock}")
            
            from .models import StockReservationLog
            # Deduct stock and log reservation
            for item in items:
                product = product_map[item["product_id"]]
                product.stock -= item["quantity"]
                product.save(update_fields=["stock"])
                
                StockReservationLog.objects.create(
                    order_id=order_id,
                    product=product,
                    quantity=item["quantity"],
                    status="RESERVED"
                )
                from .models import InventoryTransaction
                InventoryTransaction.objects.create(
                    product=product,
                    transaction_type='ORDER',
                    quantity_changed=-item["quantity"],
                    stock_after=product.stock,
                    reference_id=str(order_id),
                    notes="Deducted for order"
                )
                
                invalidate_product_cache(product.id)
                
    def release_stock(self, order_id: int, items: list):
        items = sorted(items, key=lambda x: x["product_id"])
        
        with transaction.atomic():
            product_ids = [item["product_id"] for item in items]
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            product_map = {p.id: p for p in products}
            
            from .models import StockReservationLog
            for item in items:
                p_id = item["product_id"]
                if p_id in product_map:
                    product = product_map[p_id]
                    product.stock += item["quantity"]
                    product.save(update_fields=["stock"])
                    
                    StockReservationLog.objects.create(
                        order_id=order_id,
                        product=product,
                        quantity=item["quantity"],
                        status="RELEASED"
                    )
                    from .models import InventoryTransaction
                    InventoryTransaction.objects.create(
                        product=product,
                        transaction_type='RETURN',
                        quantity_changed=item["quantity"],
                        stock_after=product.stock,
                        reference_id=str(order_id),
                        notes="Released stock from cancelled order"
                    )
                    
                    invalidate_product_cache(product.id)
