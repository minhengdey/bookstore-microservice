import logging
import os
import pickle
from collections import Counter

import requests
from django.conf import settings
from django.utils import timezone

from app.repositories import RecommenderRepository
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS, normalize_action
from app.services.behavior_prediction_service import get_behavior_prediction_service
from app.services.implicit_cf_engine import get_implicit_engine
from app.services.product_catalog import ProductCatalog

logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")
PURCHASE_CATEGORY_WEIGHT = float(os.environ.get("PURCHASE_CATEGORY_WEIGHT", "8.0"))

_order_client = None


def _get_order_client():
    global _order_client
    if _order_client is None:
        from common.client import InternalClient
        _order_client = InternalClient(timeout=8.0)
    return _order_client


def _fetch_recommender_orders(customer_id: int | None = None) -> dict:
    url = f"{ORDER_SERVICE_URL.rstrip('/')}/orders/internal/recommender-orders/"
    params = {}
    if customer_id is not None:
        params["customer_id"] = customer_id
    try:
        response = _get_order_client().get(url, params=params)
        if response.status_code == 200:
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("order-service recommender-orders unreachable: %s", exc)
    return {}


def _load_model_actions() -> list[str]:
    encoder_path = getattr(settings, "RECOMMENDER_ENCODER_PATH", None)
    if not encoder_path or not encoder_path.exists():
        return list(DEFAULT_ACTION_WEIGHTS)
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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
    Hybrid recommender:
    1. Matrix CF (NMF) from live behavior + orders
    2. Item co-occurrence (users with similar interactions)
    3. Co-purchase from order history
    4. Category affinity (content-based, novel products in preferred categories)
    5. Category-weighted fallback for cold start
    """

    def __init__(self):
        self.repo = RecommenderRepository()
        self.behavior_predictor = get_behavior_prediction_service()
        model_actions = _load_model_actions()
        self.action_weights = {
            action: DEFAULT_ACTION_WEIGHTS.get(action, 1.0)
            for action in model_actions
        }
        self.cf_weight = float(getattr(settings, "IMPLICIT_CF_ALS_WEIGHT", 4.0))
        self.cooccurrence_weight = float(getattr(settings, "COOCCURRENCE_WEIGHT", 3.0))
        self.copurchase_weight = float(getattr(settings, "COPURCHASE_WEIGHT", 2.5))
        self.category_weight = float(getattr(settings, "CATEGORY_AFFINITY_WEIGHT", 2.0))

    def predict_next_action(self, customer_id: int) -> dict | None:
        return self.behavior_predictor.predict_next_action(customer_id)

    def recommend_with_prediction(self, customer_id: int, limit: int = 10) -> dict:
        prediction = self.predict_next_action(customer_id)
        recommended_product_ids, strategy = self.recommend(
            customer_id, limit=limit, prediction=prediction
        )
        return {
            "customer_id": customer_id,
            "recommended_product_ids": recommended_product_ids,
            "next_action_prediction": prediction,
            "strategy": strategy,
        }

    def recommend(
        self,
        customer_id: int,
        limit: int = 10,
        prediction: dict | None = None,
    ) -> tuple[list[int], str]:
        catalog = ProductCatalog.get_products()
        active_product_ids = set(catalog.keys())
        if not active_product_ids:
            logger.warning("product-service returned no active products; skip recommendation scoring")
            return [], "empty-catalog"

        prediction = prediction if prediction is not None else self.predict_next_action(customer_id)
        prediction_action = (prediction or {}).get("action")
        prediction_confidence = float((prediction or {}).get("confidence") or 0.0)
        behavior_bias = self._behavior_bias(prediction_action, prediction_confidence)

        purchased = self._get_customer_products(customer_id) & active_product_ids
        interacted = self.repo.get_interacted_product_ids(customer_id) & active_product_ids
        # Hide bought items only; browsed-but-not-bought can still be suggested (e.g. same category).
        exclude = purchased
        purchase_categories = {
            int(catalog[pid]["category_id"])
            for pid in purchased
            if catalog.get(pid) and catalog[pid].get("category_id") is not None
        }

        behavior_scores = self.repo.get_behavior_scores(customer_id)
        seed_products = {
            int(pid)
            for pid, score in sorted(behavior_scores.items(), key=lambda item: item[1], reverse=True)[:8]
            if int(pid) in active_product_ids
        }
        seed_products |= purchased
        if not seed_products:
            seed_products = interacted

        category_affinity = self.repo.get_category_affinity(customer_id, catalog)
        for pid in purchased:
            meta = catalog.get(int(pid))
            if not meta or meta.get("category_id") is None:
                continue
            cat_id = int(meta["category_id"])
            category_affinity[cat_id] = category_affinity.get(cat_id, 0.0) + PURCHASE_CATEGORY_WEIGHT
        score_map: dict[int, float] = {}
        strategy_parts: list[str] = ["hybrid"]

        # 1) Matrix CF — primary signal for novel items
        cf_used = self._blend_matrix_cf(
            customer_id, score_map, active_product_ids, exclude | purchased, limit, behavior_bias
        )
        if cf_used:
            strategy_parts.append("cf")

        # 2) Co-occurrence from similar users' behavior
        cooc_scores = self.repo.get_cooccurrence_scores(customer_id, seed_products, active_product_ids)
        if cooc_scores:
            strategy_parts.append("cooccurrence")
            max_cooc = max(cooc_scores.values()) or 1.0
            for pid, score in cooc_scores.items():
                if pid in exclude:
                    continue
                norm = float(score) / max_cooc
                score_map[pid] = score_map.get(pid, 0.0) + self.cooccurrence_weight * behavior_bias * norm

        # 3) Co-purchase from orders
        copurchase = self._get_copurchase_scores(customer_id, purchased, active_product_ids)
        if copurchase:
            strategy_parts.append("copurchase")
            for pid, score in copurchase.items():
                if pid in exclude:
                    continue
                score_map[pid] = score_map.get(pid, 0.0) + self.copurchase_weight * float(score)

        # 4) Category affinity — surface unseen products in preferred categories
        if purchased:
            strategy_parts.append("purchase-category")
        if category_affinity:
            strategy_parts.append("category")
            max_affinity = max(category_affinity.values()) or 1.0
            for pid, meta in catalog.items():
                if pid in exclude:
                    continue
                cat_id = meta.get("category_id")
                if cat_id is None:
                    continue
                affinity = category_affinity.get(int(cat_id), 0.0) / max_affinity
                if affinity <= 0:
                    continue
                score_map[pid] = score_map.get(pid, 0.0) + self.category_weight * behavior_bias * affinity

        browsed_not_bought = (interacted - purchased) & active_product_ids
        for pid in browsed_not_bought:
            if pid not in score_map:
                continue
            meta = catalog.get(pid)
            cat_id = meta.get("category_id") if meta else None
            if cat_id is not None and int(cat_id) in purchase_categories:
                continue
            score_map[pid] *= 0.45

        for blocked in exclude:
            score_map.pop(blocked, None)

        recommended = [
            pid
            for pid, _ in sorted(score_map.items(), key=lambda item: item[1], reverse=True)
            if pid not in exclude
        ][:limit]

        if len(recommended) < limit:
            strategy_parts.append("fallback")
            needed = limit - len(recommended)
            fallback = self._get_category_fallback(
                catalog,
                category_affinity,
                exclude | set(recommended),
                needed,
                customer_id,
            )
            for pid in fallback:
                if pid not in recommended:
                    recommended.append(pid)
                if len(recommended) >= limit:
                    break

        if prediction_action:
            strategy_parts.append(f"next-action:{prediction_action}")

        strategy = "+".join(dict.fromkeys(strategy_parts))
        self.repo.save_log(customer_id, recommended[:limit], strategy=strategy)
        return recommended[:limit], strategy

    @staticmethod
    def _behavior_bias(prediction_action: str | None, confidence: float) -> float:
        bias = 1.0
        if prediction_action in {"purchase", "add_to_cart"}:
            bias += min(confidence, 0.9) * 0.25
        elif prediction_action in {"view", "click", "search"}:
            bias -= min(confidence, 0.9) * 0.10
        return max(0.75, bias)

    def _blend_matrix_cf(
        self,
        customer_id: int,
        score_map: dict[int, float],
        active_product_ids: set[int],
        exclude: set[int],
        limit: int,
        behavior_bias: float,
    ) -> bool:
        try:
            engine = get_implicit_engine()
            if not engine.is_ready():
                return False

            hits = engine.recommend(
                customer_id,
                exclude_product_ids=exclude,
                limit=max(limit * 5, 20),
            )
            if not hits:
                return False

            max_score = max(score for _, score in hits) or 1.0
            if max_score <= 0:
                max_score = 1.0

            weight = self.cf_weight * behavior_bias
            for pid, score in hits:
                if pid not in active_product_ids or pid in exclude:
                    continue
                norm = float(score) / max_score
                score_map[pid] = score_map.get(pid, 0.0) + weight * norm
            return True
        except Exception as exc:
            logger.warning("Matrix CF blend skipped: %s", exc)
            return False

    def _get_copurchase_scores(
        self,
        customer_id: int,
        purchased: set[int],
        active_product_ids: set[int],
    ) -> Counter:
        if not purchased:
            return Counter()

        co_buyer_products: Counter = Counter()
        for order in self._get_all_orders():
            if order.get("customer_id") == customer_id:
                continue
            items = order.get("items", [])
            order_product_ids = [
                int(i["product_id"])
                for i in items
                if i.get("product_id") in active_product_ids
            ]
            if any(pid in purchased for pid in order_product_ids):
                for pid in order_product_ids:
                    if pid not in purchased:
                        co_buyer_products[pid] += 1
        return co_buyer_products

    def _get_category_fallback(
        self,
        catalog: dict[int, dict],
        category_affinity: dict[int, float],
        exclude: set[int],
        limit: int,
        customer_id: int,
    ) -> list[int]:
        """Pick unseen products, prioritising preferred categories then catalog order."""
        if not catalog:
            return []

        by_category: dict[int | None, list[int]] = {}
        for pid, meta in catalog.items():
            if pid in exclude:
                continue
            cat_id = meta.get("category_id")
            key = int(cat_id) if cat_id is not None else None
            by_category.setdefault(key, []).append(pid)

        if not by_category:
            return []

        preferred_categories = [
            cat
            for cat, _ in sorted(category_affinity.items(), key=lambda item: item[1], reverse=True)
            if cat in by_category
        ]
        other_categories = [cat for cat in by_category if cat not in preferred_categories]

        picked: list[int] = []
        cat_idx = {cat: 0 for cat in by_category}

        def _pick_from(categories: list[int | None]) -> None:
            while len(picked) < limit:
                progressed = False
                for cat in categories:
                    items = by_category.get(cat, [])
                    idx = cat_idx.get(cat, 0)
                    while idx < len(items):
                        pid = items[idx]
                        cat_idx[cat] = idx + 1
                        idx += 1
                        if pid in exclude or pid in picked:
                            continue
                        picked.append(pid)
                        progressed = True
                        if len(picked) >= limit:
                            return
                    cat_idx[cat] = idx
                if not progressed:
                    break

        _pick_from(preferred_categories)
        if len(picked) < limit:
            _pick_from(other_categories)

        return picked[:limit]

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
        payload = _fetch_recommender_orders(customer_id=customer_id)
        purchased: set[int] = set()
        for entry in payload.get("purchase_signals") or []:
            if int(entry.get("customer_id", -1)) != int(customer_id):
                continue
            for raw in entry.get("purchase_ids") or []:
                try:
                    purchased.add(int(raw))
                except (TypeError, ValueError):
                    continue
        if purchased:
            return purchased

        for order in payload.get("orders") or []:
            if int(order.get("customer_id", -1)) != int(customer_id):
                continue
            for item in order.get("items") or []:
                pid = item.get("product_id")
                if pid is not None:
                    purchased.add(int(pid))
        return purchased

    def _get_all_orders(self) -> list:
        payload = _fetch_recommender_orders()
        orders = payload.get("orders")
        return orders if isinstance(orders, list) else []
