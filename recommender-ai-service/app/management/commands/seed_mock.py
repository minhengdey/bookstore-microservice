"""
Seed recommendation logs và behavior events (dữ liệu lớn cho CF / chatbot).
"""
import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import BehaviorEvent, RecommendationLog


STRATEGIES = [
    "collaborative",
    "content_based",
    "hybrid",
    "trending",
    "seasonal",
    "implicit_cf",
]

ACTIONS = [
    ("search", 0.5),
    ("view", 1.0),
    ("click", 1.5),
    ("add_to_cart", 3.0),
    ("purchase", 5.0),
]


class Command(BaseCommand):
    help = "Seed mock recommendation logs and behavior events"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--customers", type=int, default=int(os.getenv("MOCK_CUSTOMER_COUNT", "50")))
        parser.add_argument("--product-max-id", type=int, default=int(os.getenv("MOCK_PRODUCT_COUNT", "320")))
        parser.add_argument("--logs", type=int, default=int(os.getenv("MOCK_RECOMMENDATION_LOG_COUNT", "300")))
        parser.add_argument("--behaviors", type=int, default=int(os.getenv("MOCK_BEHAVIOR_COUNT", "8000")))

    def handle(self, *args, **options):
        rng = random.Random(42)
        customers = max(3, int(options["customers"]))
        product_max = max(24, int(options["product_max_id"]))
        log_target = max(50, int(options["logs"]))
        behavior_target = max(500, int(options["behaviors"]))

        if options.get("clear"):
            BehaviorEvent.objects.all().delete()
            RecommendationLog.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu recommender."))

        if RecommendationLog.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE(
                f"Đã có {RecommendationLog.objects.count()} logs, bỏ qua (dùng --force --clear)."
            ))
            return

        log_rows = []
        for _ in range(log_target):
            cid = rng.randint(1, customers)
            k = rng.randint(4, 12)
            product_ids = rng.sample(range(1, product_max + 1), k=min(k, product_max))
            log_rows.append(RecommendationLog(
                customer_id=cid,
                product_ids=product_ids,
                strategy=rng.choice(STRATEGIES),
            ))
        RecommendationLog.objects.bulk_create(log_rows, batch_size=500)

        behavior_rows = []
        devices = ["desktop", "mobile", "tablet"]
        personas = ["buyer", "browser", "loyal"]
        now = timezone.now()
        for _ in range(behavior_target):
            action, weight = rng.choice(ACTIONS)
            behavior_rows.append(BehaviorEvent(
                customer_id=rng.randint(1, customers),
                product_id=rng.randint(1, product_max),
                action=action,
                action_weight=weight,
                session_id=f"S{rng.randint(1000, 9999)}",
                device=rng.choice(devices),
                persona=rng.choice(personas),
                event_time=now - timedelta(
                    days=rng.randint(0, 90),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                ),
            ))
        BehaviorEvent.objects.bulk_create(behavior_rows, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(log_rows)} recommendation logs and {len(behavior_rows)} behavior events."
        ))
