import logging
import os
from collections import Counter

import requests
from django.conf import settings

from app.repositories import RecommenderRepository
from app.services.implicit_cf_engine import get_implicit_engine

logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
BOOK_SERVICE_URL = os.environ.get("BOOK_SERVICE_URL", "http://book-service:8000")
COMMENT_RATE_URL = os.environ.get("COMMENT_RATE_URL", "http://comment-rate-service:8000")


def _parse_orders_payload(data):
    if isinstance(data, dict):
        return data.get("results", data.get("orders", []))
    if isinstance(data, list):
        return data
    return []


class RecommenderService:
    """
    Hybrid gợi ý:
    1. Implicit ALS (offline train từ CSV / Kaggle) — nếu đã train và user có trong tập
    2. Co-purchase (cùng mua) + điểm hành vi
    3. Fallback: sách đầu danh mục từ book-service
    """

    def __init__(self):
        self.repo = RecommenderRepository()
        self.action_weights = {
            "click": 0.5,
            "view": 1.0,
            "wishlist": 2.0,
            "cart_add": 3.0,
            "purchase": 4.0,
            "review": 2.5,
        }

    def recommend(self, customer_id: int, limit: int = 10) -> list:
        customer_books = self._get_customer_books(customer_id)
        behavior_scores = self.repo.get_behavior_scores(customer_id)

        all_orders = self._get_all_orders()
        co_buyer_books = Counter()
        for order in all_orders:
            if order.get("customer_id") == customer_id:
                continue
            items = order.get("items", [])
            order_book_ids = [i["book_id"] for i in items]
            if any(bid in customer_books for bid in order_book_ids):
                for bid in order_book_ids:
                    if bid not in customer_books:
                        co_buyer_books[bid] += 1

        score_map: dict[int, float] = {int(k): float(v) for k, v in behavior_scores.items()}
        for bid, score in co_buyer_books.items():
            score_map[bid] = score_map.get(bid, 0.0) + float(score)

        als_weight = float(getattr(settings, "IMPLICIT_CF_ALS_WEIGHT", 4.0))
        try:
            eng = get_implicit_engine()
            if eng.is_ready():
                als_hits = eng.recommend(
                    customer_id,
                    exclude_book_ids=customer_books,
                    limit=max(limit * 3, limit),
                )
                if als_hits:
                    max_s = max(s for _, s in als_hits)
                    if max_s <= 0:
                        max_s = 1.0
                    for bid, sc in als_hits:
                        norm = float(sc) / max_s
                        score_map[bid] = score_map.get(bid, 0.0) + als_weight * norm
        except Exception as e:
            logger.warning("ALS blend skipped: %s", e)

        for bought_book_id in customer_books:
            score_map.pop(bought_book_id, None)

        recommended = [
            bid
            for bid, _ in sorted(score_map.items(), key=lambda item: item[1], reverse=True)[:limit]
        ]

        if len(recommended) < limit:
            top_rated = self._get_top_rated_books(limit)
            for bid in top_rated:
                if bid not in customer_books and bid not in recommended:
                    recommended.append(bid)
                if len(recommended) >= limit:
                    break

        self.repo.save_log(customer_id, recommended[:limit])
        return recommended[:limit]

    def track_behavior(self, customer_id: int, book_id: int, action: str):
        normalized_action = (action or "").strip().lower()
        if normalized_action == "click":
            # Keep compatibility with existing DB constraint that does not include "click".
            normalized_action = "view"
        if normalized_action not in self.action_weights:
            raise ValueError("Unsupported action type")
        return self.repo.save_behavior(
            customer_id=customer_id,
            book_id=book_id,
            action=normalized_action,
            action_weight=self.action_weights[normalized_action],
        )

    def _get_customer_books(self, customer_id: int) -> set:
        try:
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/?customer_id={customer_id}", timeout=5)
            if r.status_code == 200:
                orders = _parse_orders_payload(r.json())
                return {item["book_id"] for order in orders for item in order.get("items", [])}
        except requests.exceptions.RequestException as e:
            logger.warning(f"order-service unreachable: {e}")
        return set()

    def _get_all_orders(self) -> list:
        try:
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/", timeout=5)
            if r.status_code == 200:
                return _parse_orders_payload(r.json())
        except requests.exceptions.RequestException as e:
            logger.warning(f"order-service unreachable: {e}")
        return []

    def _get_top_rated_books(self, limit: int) -> list:
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
            if r.status_code == 200:
                data = r.json()
                books = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(books, list):
                    return [b["id"] for b in books[:limit]]
        except requests.exceptions.RequestException:
            pass
        return []
