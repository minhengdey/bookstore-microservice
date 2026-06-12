"""Map external interaction / payment events into BehaviorEvent rows."""
from __future__ import annotations

import logging

from django.utils import timezone

from app.models import BehaviorEvent
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS, normalize_action

logger = logging.getLogger(__name__)

INTERACTION_TO_BEHAVIOR = {
    "VIEW": "view",
    "CLICK": "click",
    "SEARCH": "search",
    "ADD_TO_CART": "add_to_cart",
    "ADDED_TO_CART": "add_to_cart",
    "REMOVE_FROM_CART": "remove_from_cart",
    "WISHLIST": "wishlist",
    "PURCHASE": "purchase",
    "REVIEW": "review",
    "RATING": "review",
}


def record_behavior_from_interaction(
    user_id,
    product_id,
    event_type: str,
    weight: float | None = None,
    session_id: str | None = None,
    device: str | None = None,
) -> bool:
    action = INTERACTION_TO_BEHAVIOR.get((event_type or "").upper())
    if not action:
        return False
    try:
        customer_id = int(user_id)
        pid = int(product_id)
    except (TypeError, ValueError):
        return False

    normalized = normalize_action(action)
    if normalized not in DEFAULT_ACTION_WEIGHTS:
        return False

    BehaviorEvent.objects.create(
        customer_id=customer_id,
        product_id=pid,
        action=normalized,
        action_weight=float(weight if weight is not None else DEFAULT_ACTION_WEIGHTS[normalized]),
        session_id=session_id,
        device=device,
        event_time=timezone.now(),
    )
    return True
