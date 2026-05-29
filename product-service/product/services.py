from django.db import transaction
import redis
import json
import os
from .models import Product, Category

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

class ProductService:
    def list(self): return Product.objects.select_related("category").all()
    def get(self, pk):
        p = Product.objects.select_related("category").filter(pk=pk).first()
        if not p: raise ValueError(f"Product {pk} not found")
        return p

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
                    
                    invalidate_product_cache(product.id)
