import os
import json
import redis
from .catalog_client import CatalogClient

class CartService:
    def __init__(self):
        redis_url = os.environ.get('REDIS_URL', 'redis://order-redis:6379/0')
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = 7 * 24 * 3600  # 7 days

    def _get_key(self, user_id: str) -> str:
        return f"cart:{user_id}"

    def get_cart(self, user_id: str) -> list:
        key = self._get_key(user_id)
        items = self.redis_client.hgetall(key)
        return [{"variant_id": k, "quantity": int(v)} for k, v in items.items()]

    def add_item(self, user_id: str, variant_id: str, quantity: int) -> dict:
        # Validate existence of product synchronously against Catalog API
        # but do NOT check stock, to avoid high concurrency bottlenecks.
        variant = CatalogClient.get_variant(variant_id)
        if not variant:
            raise ValueError(f"Variant {variant_id} does not exist in catalog")
            
        key = self._get_key(user_id)
        self.redis_client.hincrby(key, variant_id, quantity)
        self.redis_client.expire(key, self.ttl)
        
        return {"variant_id": variant_id, "quantity_added": quantity, "catalog_verified": True}

    def remove_item(self, user_id: str, variant_id: str) -> bool:
        key = self._get_key(user_id)
        result = self.redis_client.hdel(key, variant_id)
        return result > 0

    def clear_cart(self, user_id: str):
        key = self._get_key(user_id)
        self.redis_client.delete(key)
