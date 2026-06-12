"""
Backfill purchase BehaviorEvent rows from order-service (paid/placed orders).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import BehaviorEvent
from app.services.behavior_actions import DEFAULT_ACTION_WEIGHTS
from app.services.recommender_service import _fetch_recommender_orders


class Command(BaseCommand):
    help = "Sync purchase behavior events from order history."

    def handle(self, *args, **options):
        payload = _fetch_recommender_orders()
        purchase_weight = float(DEFAULT_ACTION_WEIGHTS.get("purchase", 5.0))
        created = 0

        for order in payload.get("orders") or []:
            customer_id = order.get("customer_id")
            if customer_id is None:
                continue
            for item in order.get("items") or []:
                product_id = item.get("product_id")
                if product_id is None:
                    continue
                exists = BehaviorEvent.objects.filter(
                    customer_id=int(customer_id),
                    product_id=int(product_id),
                    action="purchase",
                ).exists()
                if exists:
                    continue
                BehaviorEvent.objects.create(
                    customer_id=int(customer_id),
                    product_id=int(product_id),
                    action="purchase",
                    action_weight=purchase_weight,
                    event_time=timezone.now(),
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Synced {created} purchase behavior events."))
