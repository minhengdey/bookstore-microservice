"""Cached product catalog from product-service for recommendation scoring."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")
_CACHE_TTL_SECONDS = 300


class ProductCatalog:
    _products: dict[int, dict[str, Any]] | None = None
    _loaded_at: float = 0.0

    @classmethod
    def get_products(cls, force_refresh: bool = False) -> dict[int, dict[str, Any]]:
        now = time.time()
        if (
            not force_refresh
            and cls._products is not None
            and (now - cls._loaded_at) < _CACHE_TTL_SECONDS
        ):
            return cls._products

        products: dict[int, dict[str, Any]] = {}
        page = 1
        page_size = 200
        max_pages = 50

        while page <= max_pages:
            try:
                response = requests.get(
                    f"{PRODUCT_SERVICE_URL.rstrip('/')}/products/",
                    params={"page": page, "page_size": page_size},
                    timeout=8,
                )
                if response.status_code != 200:
                    break

                data = response.json()
                chunk = data.get("results", data) if isinstance(data, dict) else data
                if not isinstance(chunk, list) or not chunk:
                    break

                for raw in chunk:
                    if not isinstance(raw, dict) or raw.get("id") is None:
                        continue
                    pid = int(raw["id"])
                    category = raw.get("category") or {}
                    category_id = raw.get("category_id")
                    if category_id is None and isinstance(category, dict):
                        category_id = category.get("id")
                    category_name = None
                    if isinstance(category, dict):
                        category_name = category.get("name") or category.get("category_name")
                    products[pid] = {
                        "id": pid,
                        "name": raw.get("name") or raw.get("title") or "",
                        "category_id": int(category_id) if category_id is not None else None,
                        "category_name": category_name,
                        "price": float(raw.get("price") or 0),
                    }

                if isinstance(data, dict):
                    next_page = data.get("next_page")
                    if next_page in (None, "", False):
                        break
                    page = int(next_page) if isinstance(next_page, int) else page + 1
                else:
                    break
            except requests.exceptions.RequestException as exc:
                logger.warning("product-service unreachable while loading catalog: %s", exc)
                break

        if products:
            cls._products = products
            cls._loaded_at = now
        elif cls._products is not None:
            return cls._products

        cls._products = products
        cls._loaded_at = now
        return products

    @classmethod
    def get_active_ids(cls) -> set[int]:
        return set(cls.get_products().keys())

    @classmethod
    def invalidate(cls) -> None:
        cls._products = None
        cls._loaded_at = 0.0
