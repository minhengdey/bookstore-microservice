"""
Centralized behavior tracking for recommender-ai-service.

Every storefront action that should influence recommendations must go through
track_behavior() so the recommender DB and (optionally) interaction event bus
stay in sync.
"""
from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SVC = settings.SERVICE_URLS

# Actions accepted by recommender-ai-service (see behavior_actions.DEFAULT_ACTION_WEIGHTS)
SUPPORTED_ACTIONS = frozenset({
    "search",
    "view",
    "click",
    "wishlist",
    "add_to_cart",
    "remove_from_cart",
    "purchase",
    "review",
})

_INTERACTION_EVENT_MAP = {
    "search": "SEARCH",
    "view": "VIEW",
    "click": "CLICK",
    "wishlist": "WISHLIST",
    "add_to_cart": "ADD_TO_CART",
    "remove_from_cart": "REMOVE_FROM_CART",
    "purchase": "PURCHASE",
    "review": "REVIEW",
}


def _client_device(request) -> str:
    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()
    if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
        return "mobile"
    if "ipad" in user_agent or "tablet" in user_agent:
        return "tablet"
    return "desktop"


def _persona(request) -> str:
    from .permissions import _role
    return _role(request) or "anonymous"


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def _auth_headers(request) -> dict:
    payload = getattr(request, "jwt_payload", None)
    if not payload:
        return {}
    roles = payload.get("roles", [])
    role_str = (",".join(roles) if isinstance(roles, list) else str(roles)).lower()
    return {
        "X-User-Id": str(payload.get("user_id", "")),
        "X-Roles": role_str,
        "X-User-Role": role_str,
        "X-Role": role_str,
        "X-Entity-Id": str(payload.get("entity_id", "")),
        "X-Username": str(payload.get("username", "")),
    }


def track_behavior(request, customer_id, product_id, action: str) -> bool:
    """
    Record a behavior event. Returns True when recommender accepted the event.
    """
    if customer_id is None or product_id is None:
        return False

    normalized = (action or "").strip().lower()
    aliases = {
        "cart_add": "add_to_cart",
        "add-cart": "add_to_cart",
        "add_cart": "add_to_cart",
        "remove-cart": "remove_from_cart",
        "remove_cart": "remove_from_cart",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_ACTIONS:
        logger.warning("[behavior] unsupported action=%s product=%s", action, product_id)
        return False

    try:
        customer_id = int(customer_id)
        product_id = int(product_id)
    except (TypeError, ValueError):
        return False

    session_id = _session_key(request)
    device = _client_device(request)
    persona = _persona(request)
    ok = _post_recommender_event(
        request,
        customer_id=customer_id,
        product_id=product_id,
        action=normalized,
        session_id=session_id,
        device=device,
        persona=persona,
    )
    _post_interaction_event(
        customer_id=customer_id,
        product_id=product_id,
        action=normalized,
        session_id=session_id,
    )
    return ok


def track_order_purchases(request, order: dict | None) -> int:
    if not order or not isinstance(order, dict):
        return 0
    customer_id = order.get("customer_id")
    if customer_id is None:
        return 0
    count = 0
    for item in order.get("items") or []:
        product_id = item.get("product_id")
        if product_id is None:
            continue
        if track_behavior(request, customer_id, int(product_id), "purchase"):
            count += 1
    return count


def _post_recommender_event(
    request,
    *,
    customer_id: int,
    product_id: int,
    action: str,
    session_id: str,
    device: str,
    persona: str,
) -> bool:
    try:
        response = requests.post(
            f"{SVC['recommender']}/api/recommender/events/",
            json={
                "customer_id": customer_id,
                "product_id": product_id,
                "action": action,
                "session_id": session_id,
                "device": device,
                "persona": persona,
            },
            headers=_auth_headers(request),
            timeout=3,
        )
        if response.status_code == 201:
            return True
        logger.warning(
            "[behavior] recommender rejected action=%s customer=%s product=%s status=%s body=%s",
            action,
            customer_id,
            product_id,
            response.status_code,
            response.text[:200],
        )
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "[behavior] recommender unreachable action=%s customer=%s product=%s: %s",
            action,
            customer_id,
            product_id,
            exc,
        )
    return False


def _post_interaction_event(
    *,
    customer_id: int,
    product_id: int,
    action: str,
    session_id: str,
) -> None:
    event_type = _INTERACTION_EVENT_MAP.get(action)
    if not event_type:
        return
    base = SVC.get("interaction", "").rstrip("/")
    if not base:
        return
    url = f"{base}/api/v1/interactions/interactions/"
    try:
        requests.post(
            url,
            json={
                "user_id": str(customer_id),
                "product_id": str(product_id),
                "event_type": event_type,
                "session_id": session_id,
                "source": "WEB",
                "idempotency_key": f"{customer_id}:{product_id}:{action}:{uuid.uuid4().hex[:12]}",
            },
            timeout=2,
        )
    except requests.exceptions.RequestException as exc:
        logger.debug(
            "[behavior] interaction bus skipped action=%s customer=%s product=%s: %s",
            action,
            customer_id,
            product_id,
            exc,
        )
