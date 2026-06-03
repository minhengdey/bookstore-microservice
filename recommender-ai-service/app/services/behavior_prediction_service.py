from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests
from django.conf import settings

from app.models import BehaviorEvent
from app.services.behavior_actions import normalize_action


logger = logging.getLogger(__name__)


class BehaviorPredictionService:
    _predictor = None
    _product_cache: dict[int, dict[str, Any]] = {}

    def __init__(self) -> None:
        self.model_path = getattr(settings, "RECOMMENDER_MODEL_PATH", None)
        self.encoder_path = getattr(settings, "RECOMMENDER_ENCODER_PATH", None)
        self.product_service_url = getattr(settings, "PRODUCT_SERVICE_URL", "http://product-service:8000").rstrip("/")

    def _get_predictor(self):
        if self._predictor is not None:
            return self._predictor

        if not self.model_path or not self.encoder_path:
            logger.warning("Behavior predictor paths are not configured")
            return None

        if not self.model_path.exists() or not self.encoder_path.exists():
            logger.warning("Behavior predictor artifacts not found: %s | %s", self.model_path, self.encoder_path)
            return None

        try:
            from inference_utils import UserBehaviorPredictor

            self._predictor = UserBehaviorPredictor(str(self.model_path), str(self.encoder_path))
        except Exception as exc:
            logger.warning("Failed to load behavior predictor: %s", exc)
            self._predictor = None
        return self._predictor

    @staticmethod
    def _normalize_action(action: str | None) -> str:
        return normalize_action(action)

    @staticmethod
    def _goal_from_action(action: str | None) -> str:
        normalized = BehaviorPredictionService._normalize_action(action)
        if normalized in {"view", "click", "search"}:
            return "browsing"
        if normalized in {"add_to_cart", "purchase"}:
            return "buying"
        if normalized == "review":
            return "reviewing"
        if normalized == "wishlist":
            return "comparing"
        if normalized == "remove_from_cart":
            return "abandoning"
        return "browsing"

    @staticmethod
    def _price_tier(price: float | int | None) -> str:
        try:
            value = float(price or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value <= 100_000:
            return "low"
        if value <= 300_000:
            return "mid"
        return "high"

    def _fetch_product_metadata(self, product_id: int) -> dict[str, Any]:
        if product_id in self._product_cache:
            return self._product_cache[product_id]

        metadata: dict[str, Any] = {"category": "products", "price": 0.0, "price_tier": "low"}
        try:
            response = requests.get(f"{self.product_service_url}/products/{product_id}/", timeout=4)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    category = payload.get("category") or {}
                    if isinstance(category, dict):
                        category_name = category.get("name") or category.get("category_name") or category.get("title")
                    else:
                        category_name = None
                    price = payload.get("price", 0)
                    metadata = {
                        "category": (str(category_name).strip().lower() if category_name else "products"),
                        "price": float(price or 0),
                        "price_tier": self._price_tier(price),
                    }
        except requests.exceptions.RequestException:
            pass

        self._product_cache[product_id] = metadata
        return metadata

    def _build_dataframe(self, events: list[BehaviorEvent]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        purchase_count = 0

        for index, event in enumerate(events):
            product_meta = self._fetch_product_metadata(int(event.product_id))
            normalized_action = self._normalize_action(event.action)
            if normalized_action == "purchase":
                purchase_count += 1

            timestamp = event.event_time
            session_id = event.session_id or f"customer-{event.customer_id}"
            rows.append(
                {
                    "customer_id": int(event.customer_id),
                    "action": normalized_action,
                    "category": product_meta["category"],
                    "device": (event.device or "desktop").strip().lower() or "desktop",
                    "product_id": int(event.product_id),
                    "price_tier": product_meta["price_tier"],
                    "hour": timestamp.hour if timestamp else 0,
                    "day_of_week": timestamp.weekday() if timestamp else 0,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "purchase_count": purchase_count,
                    "goal": self._goal_from_action(normalized_action),
                    "sequence_index": index,
                }
            )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        return df.sort_values("timestamp").reset_index(drop=True)

    def predict_next_action(self, customer_id: int) -> dict[str, Any] | None:
        predictor = self._get_predictor()
        if predictor is None:
            return None

        events = list(
            BehaviorEvent.objects.filter(customer_id=customer_id)
            .order_by("event_time")
            .values("customer_id", "product_id", "action", "session_id", "device", "event_time")
        )
        if not events:
            return None

        event_objects = [
            BehaviorEvent(
                customer_id=row["customer_id"],
                product_id=row["product_id"],
                action=row["action"],
                session_id=row.get("session_id"),
                device=row.get("device"),
                event_time=row["event_time"],
            )
            for row in events
        ]

        df_user = self._build_dataframe(event_objects)
        if df_user.empty:
            return None

        prediction = predictor.predict(df_user)
        if not prediction:
            return None

        return {
            **prediction,
            "customer_id": int(customer_id),
            "observed_events": int(len(df_user)),
            "model_ready": True,
        }


_service: BehaviorPredictionService | None = None


def get_behavior_prediction_service() -> BehaviorPredictionService:
    global _service
    if _service is None:
        _service = BehaviorPredictionService()
    return _service