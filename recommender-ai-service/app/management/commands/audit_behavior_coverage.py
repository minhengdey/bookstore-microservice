"""
Audit which behavior actions are configured, observed in DB, and reachable via API.
"""
import os

import requests
from django.core.management.base import BaseCommand

from app.models import BehaviorEvent
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS, normalize_action


EXPECTED_TOUCHPOINTS = {
    "search": "product_list search (api-gateway)",
    "view": "product_detail GET (api-gateway)",
    "click": "product_detail GET (api-gateway)",
    "add_to_cart": "product_detail/cart/recommendations POST (api-gateway)",
    "remove_from_cart": "cart remove (api-gateway)",
    "purchase": "checkout COD / payment callback + order sync (api-gateway)",
    "wishlist": "product_wishlist_toggle add (api-gateway)",
    "review": "product_review POST (api-gateway)",
}


class Command(BaseCommand):
    help = "Report behavior action coverage for recommender-ai-service."

    def handle(self, *args, **options):
        self.stdout.write("=== Behavior action weights ===")
        for action, weight in DEFAULT_ACTION_WEIGHTS.items():
            count = BehaviorEvent.objects.filter(action=action).count()
            touchpoint = EXPECTED_TOUCHPOINTS.get(action, "n/a")
            self.stdout.write(f"  {action:18} weight={weight:4} events={count:5}  via {touchpoint}")

        self.stdout.write("\n=== Unknown actions in DB ===")
        known = set(DEFAULT_ACTION_WEIGHTS)
        unknown = (
            BehaviorEvent.objects.exclude(action__in=known)
            .values_list("action", flat=True)
            .distinct()
        )
        if unknown:
            for action in unknown:
                self.stdout.write(self.style.WARNING(f"  {action}"))
        else:
            self.stdout.write("  (none)")

        self.stdout.write("\n=== API smoke test ===")
        recommender = os.environ.get("RECOMMENDER_SELF_URL", "http://127.0.0.1:8000")
        for action in DEFAULT_ACTION_WEIGHTS:
            try:
                response = requests.post(
                    f"{recommender.rstrip('/')}/api/recommender/events/",
                    json={
                        "customer_id": 0,
                        "product_id": 0,
                        "action": action,
                        "session_id": "audit",
                        "device": "desktop",
                    },
                    timeout=3,
                )
                ok = response.status_code == 201
                style = self.style.SUCCESS if ok else self.style.ERROR
                self.stdout.write(style(f"  POST {action}: {response.status_code}"))
                if ok:
                    BehaviorEvent.objects.filter(customer_id=0, product_id=0, action=normalize_action(action)).delete()
            except requests.exceptions.RequestException as exc:
                self.stdout.write(self.style.ERROR(f"  POST {action}: unreachable ({exc})"))

        self.stdout.write(self.style.SUCCESS("\nAudit complete."))
