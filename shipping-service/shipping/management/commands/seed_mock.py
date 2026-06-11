from django.core.management.base import BaseCommand
from shipping.models import ShippingMethod


class Command(BaseCommand):
    help = "Seed default shipping methods"

    def handle(self, *args, **options):
        if ShippingMethod.objects.exists():
            self.stdout.write(self.style.NOTICE("Shipping methods already exist, skipping."))
            return
        methods = [
            {"method_name": "Giao hàng tiêu chuẩn", "description": "3-5 ngày", "rate": 25000, "min_weight": 0, "max_weight": 10, "min_distance": 0, "max_distance": 50},
            {"method_name": "Giao hàng nhanh", "description": "1-2 ngày", "rate": 45000, "min_weight": 0, "max_weight": 5, "min_distance": 0, "max_distance": 30},
            {"method_name": "Giao hàng tiết kiệm", "description": "5-7 ngày", "rate": 15000, "min_weight": 0, "max_weight": 20, "min_distance": 0, "max_distance": 100},
        ]
        for m in methods:
            ShippingMethod.objects.create(**m)
        self.stdout.write(self.style.SUCCESS(f"Created {len(methods)} shipping methods."))
