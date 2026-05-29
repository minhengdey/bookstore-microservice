import logging
import os
from collections import Counter
import random
import pickle

import requests
from django.conf import settings
from django.utils import timezone

from app.repositories import RecommenderRepository
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS, normalize_action
from app.services.behavior_prediction_service import get_behavior_prediction_service
from app.services.implicit_cf_engine import get_implicit_engine

logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
BOOK_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")
COMMENT_RATE_URL = os.environ.get("COMMENT_RATE_URL", "http://comment-rate-service:8000")

def _load_model_actions() -> list[str]:
    encoder_path = getattr(settings, "RECOMMENDER_ENCODER_PATH", None)
    if not encoder_path or not encoder_path.exists():
        return list(DEFAULT_ACTION_WEIGHTS)
    try:
        with open(encoder_path, "rb") as f:
            encoders = pickle.load(f)
        return [str(action) for action in encoders.get("ACTIONS", [])]
    except Exception as exc:
        logger.warning("Failed to load recommender action classes: %s", exc)
        return list(DEFAULT_ACTION_WEIGHTS)


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
        self.behavior_predictor = get_behavior_prediction_service()
        model_actions = _load_model_actions()
        self.action_weights = {
            action: DEFAULT_ACTION_WEIGHTS.get(action, 1.0)
            for action in model_actions
        }

    def predict_next_action(self, customer_id: int) -> dict | None:
        return self.behavior_predictor.predict_next_action(customer_id)

    def recommend_with_prediction(self, customer_id: int, limit: int = 10) -> dict:
        prediction = self.predict_next_action(customer_id)
        recommended_product_ids = self.recommend(customer_id, limit=limit, prediction=prediction)
        return {
            "customer_id": customer_id,
            "recommended_product_ids": recommended_product_ids,
            "next_action_prediction": prediction,
        }

    def recommend(self, customer_id: int, limit: int = 10, prediction: dict | None = None) -> list:
        active_product_ids = self._get_active_product_ids()
        if not active_product_ids:
            logger.warning("product-service returned no active products; skip recommendation scoring")
            return []

        prediction = prediction if prediction is not None else self.predict_next_action(customer_id)
        prediction_action = (prediction or {}).get("action")
        prediction_confidence = float((prediction or {}).get("confidence") or 0.0)
        behavior_bias = 1.0
        if prediction_action in {"purchase", "add_to_cart"}:
            behavior_bias += min(prediction_confidence, 0.9) * 0.25
        elif prediction_action in {"view", "click", "search"}:
            behavior_bias -= min(prediction_confidence, 0.9) * 0.10
        behavior_bias = max(0.75, behavior_bias)

        customer_products = self._get_customer_products(customer_id)
        customer_products = {pid for pid in customer_products if pid in active_product_ids}
        behavior_scores = self.repo.get_behavior_scores(customer_id)

        all_orders = self._get_all_orders()
        co_buyer_products = Counter()
        for order in all_orders:
            if order.get("customer_id") == customer_id:
                continue
            items = order.get("items", [])
            order_product_ids = [i["product_id"] for i in items if i.get("product_id") in active_product_ids]
            if any(pid in customer_products for pid in order_product_ids):
                for pid in order_product_ids:
                    if pid not in customer_products:
                        co_buyer_products[pid] += 1

        score_map: dict[int, float] = {
            int(k): float(v)
            for k, v in behavior_scores.items()
            if int(k) in active_product_ids
        }
        for pid, score in co_buyer_products.items():
            score_map[pid] = score_map.get(pid, 0.0) + float(score)

        als_weight = float(getattr(settings, "IMPLICIT_CF_ALS_WEIGHT", 4.0)) * behavior_bias
        try:
            eng = get_implicit_engine()
            if eng.is_ready():
                als_hits = eng.recommend(
                    customer_id,
                    exclude_product_ids=customer_products,
                    limit=max(limit * 3, limit),
                )
                if als_hits:
                    max_s = max(s for _, s in als_hits)
                    if max_s <= 0:
                        max_s = 1.0
                    for bid, sc in als_hits:
                        norm = float(sc) / max_s
                        if bid in active_product_ids:
                            score_map[bid] = score_map.get(bid, 0.0) + als_weight * norm
        except Exception as e:
            logger.warning("ALS blend skipped: %s", e)

        for bought_product_id in customer_products:
            score_map.pop(bought_product_id, None)

        recommended = [
            bid
            for bid, _ in sorted(score_map.items(), key=lambda item: item[1], reverse=True)[:limit]
        ]

        # Cold-start hint: if no behavior/order/ALS signal, prioritize diversified fallback.
        no_personal_signal = len(recommended) == 0

        if len(recommended) < limit:
            top_rated = self._get_top_rated_products(limit, customer_id=customer_id, diversify=no_personal_signal)
            for pid in top_rated:
                if pid not in customer_products and pid not in recommended:
                    recommended.append(pid)
                if len(recommended) >= limit:
                    break

        strategy = "hybrid"
        if prediction_action:
            strategy = f"{strategy}+next-action:{prediction_action}"
        self.repo.save_log(customer_id, recommended[:limit], strategy=strategy)
        return recommended[:limit]

    def track_behavior(self, customer_id: int, product_id: int, action: str, **kwargs):
        normalized_action = normalize_action(action)

        if normalized_action not in self.action_weights:
            raise ValueError(f"Unsupported action type: {normalized_action}")

        event_time = kwargs.pop("event_time", None) or timezone.now()
        return self.repo.save_behavior(
            customer_id=customer_id,
            product_id=product_id,
            action=normalized_action,
            action_weight=self.action_weights[normalized_action],
            event_time=event_time,
            **kwargs
        )

    def _get_customer_products(self, customer_id: int) -> set:
        try:
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/?customer_id={customer_id}", timeout=5)
            if r.status_code == 200:
                orders = _parse_orders_payload(r.json())
                return {item["product_id"] for order in orders for item in order.get("items", [])}
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

    def _get_top_rated_products(self, limit: int, customer_id: int | None = None, diversify: bool = False) -> list:
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/products/", params={"page_size": 200}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                products = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(products, list):
                    if not diversify:
                        return [b["id"] for b in products[:limit] if isinstance(b, dict) and b.get("id") is not None]

                    # Diversified fallback for new users:
                    # 1) group by category
                    # 2) deterministic shuffle using customer_id seed
                    # 3) round-robin between categories
                    by_category: dict[str, list[dict]] = {}
                    for p in products:
                        if not isinstance(p, dict) or p.get("id") is None:
                            continue
                        cat_key = str(p.get("category_id", "unknown"))
                        by_category.setdefault(cat_key, []).append(p)

                    rng = random.Random(str(customer_id or "anonymous"))
                    category_keys = list(by_category.keys())
                    rng.shuffle(category_keys)
                    for cat in category_keys:
                        rng.shuffle(by_category[cat])

                    picked_ids = []
                    cat_idx = {cat: 0 for cat in category_keys}
                    while len(picked_ids) < limit:
                        progressed = False
                        for cat in category_keys:
                            idx = cat_idx[cat]
                            items = by_category[cat]
                            if idx >= len(items):
                                continue
                            pid = items[idx].get("id")
                            cat_idx[cat] = idx + 1
                            if pid is None or pid in picked_ids:
                                continue
                            picked_ids.append(pid)
                            progressed = True
                            if len(picked_ids) >= limit:
                                break
                        if not progressed:
                            break
                    return picked_ids
        except requests.exceptions.RequestException:
            pass
        return []

    def _get_active_product_ids(self) -> set:
        product_ids = set()
        page = 1
        page_size = 200
        max_pages = 50

        while page <= max_pages:
            try:
                r = requests.get(
                    f"{BOOK_SERVICE_URL}/products/",
                    params={"page": page, "page_size": page_size},
                    timeout=5,
                )
                if r.status_code != 200:
                    break

                data = r.json()
                products = data.get("results", data) if isinstance(data, dict) else data
                if not isinstance(products, list) or not products:
                    break

                for p in products:
                    pid = p.get("id") if isinstance(p, dict) else None
                    if pid is not None:
                        product_ids.add(int(pid))

                if isinstance(data, dict):
                    next_page = data.get("next_page")
                    if next_page in (None, "", False):
                        break
                    if isinstance(next_page, int):
                        page = next_page
                    else:
                        page += 1
                else:
                    break
            except requests.exceptions.RequestException as e:
                logger.warning("product-service unreachable: %s", e)
                break

        return product_ids
