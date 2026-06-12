"""
Backfill wishlist + review rows from interaction-service into BehaviorEvent.
"""
import os

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import BehaviorEvent
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS


def _interaction_base() -> str:
    return os.environ.get("INTERACTION_SERVICE_URL", "http://interaction-service:8000").rstrip("/")


def _fetch_all(url: str) -> list[dict]:
    page = 1
    rows: list[dict] = []
    while page <= 100:
        try:
            response = requests.get(url, params={"page": page, "page_size": 200}, timeout=10)
            if response.status_code != 200:
                break
            payload = response.json()
            chunk = payload.get("results", payload) if isinstance(payload, dict) else payload
            if not isinstance(chunk, list) or not chunk:
                break
            rows.extend(chunk)
            if isinstance(payload, dict) and payload.get("next"):
                page += 1
            else:
                break
        except requests.exceptions.RequestException:
            break
    return rows


class Command(BaseCommand):
    help = "Sync wishlist/review interactions into BehaviorEvent."

    def handle(self, *args, **options):
        base = _interaction_base()
        created = 0

        for row in _fetch_all(f"{base}/api/v1/interactions/wishlists/"):
            customer_id = row.get("customer_id")
            product_id = row.get("product_id")
            if customer_id is None or product_id is None:
                continue
            if BehaviorEvent.objects.filter(
                customer_id=int(customer_id),
                product_id=int(product_id),
                action="wishlist",
            ).exists():
                continue
            BehaviorEvent.objects.create(
                customer_id=int(customer_id),
                product_id=int(product_id),
                action="wishlist",
                action_weight=float(DEFAULT_ACTION_WEIGHTS["wishlist"]),
                event_time=timezone.now(),
            )
            created += 1

        for row in _fetch_all(f"{base}/api/v1/interactions/reviews/"):
            customer_id = row.get("customer_id")
            product_id = row.get("product_id")
            if customer_id is None or product_id is None:
                continue
            if BehaviorEvent.objects.filter(
                customer_id=int(customer_id),
                product_id=int(product_id),
                action="review",
            ).exists():
                continue
            BehaviorEvent.objects.create(
                customer_id=int(customer_id),
                product_id=int(product_id),
                action="review",
                action_weight=float(DEFAULT_ACTION_WEIGHTS["review"]),
                event_time=timezone.now(),
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Synced {created} wishlist/review behavior events."))
