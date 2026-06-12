"""
Seed đơn hàng legacy mẫu (nhiều trạng thái).
Chạy: python manage.py seed_mock --clear --force
"""
import os
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from order.legacy_models import LegacyOrder, LegacyOrderItem, OrderStatus


STATUSES = [
    OrderStatus.DELIVERED,
    OrderStatus.DELIVERED,
    OrderStatus.SHIPPING,
    OrderStatus.PROCESSING,
    OrderStatus.PAID,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.CANCELLED,
    OrderStatus.RETURNED,
]


class Command(BaseCommand):
    help = "Seed legacy orders and order items"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument(
            "--orders",
            type=int,
            default=int(os.getenv("MOCK_ORDER_COUNT", "250")),
        )
        parser.add_argument(
            "--customers",
            type=int,
            default=int(os.getenv("MOCK_CUSTOMER_COUNT", "50")),
        )
        parser.add_argument(
            "--product-max-id",
            type=int,
            default=int(os.getenv("MOCK_PRODUCT_COUNT", "320")),
        )

    def handle(self, *args, **options):
        order_count = max(20, int(options["orders"]))
        customer_count = max(3, int(options["customers"]))
        product_max = max(24, int(options["product_max_id"]))
        rng = random.Random(7)

        if options.get("clear"):
            LegacyOrderItem.objects.all().delete()
            LegacyOrder.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu order."))

        if LegacyOrder.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE(
                f"Đã có {LegacyOrder.objects.count()} orders, bỏ qua (dùng --force --clear)."
            ))
            return

        cities = ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Cần Thơ", "Hải Phòng"]
        created = 0
        for _ in range(order_count):
            customer_id = rng.randint(1, customer_count)
            status = rng.choice(STATUSES)
            item_n = rng.randint(1, 4)
            subtotal = Decimal("0")
            order = LegacyOrder.objects.create(
                customer_id=customer_id,
                status=status,
                shipping_fee=Decimal(str(rng.choice([0, 15000, 25000, 45000]))),
                discount_amount=Decimal("0"),
                total_amount=Decimal("0"),
                shipping_address_snapshot={
                    "full_name": f"Khách hàng {customer_id}",
                    "phone": f"09{rng.randint(10000000, 99999999)}",
                    "address": f"{rng.randint(1, 999)} Đường {rng.randint(1, 50)}",
                    "city": rng.choice(cities),
                },
                voucher_code=rng.choice(["", "", "WELCOME10", "SAVE50K"]),
            )
            order.order_date = timezone.now() - timedelta(days=rng.randint(0, 120))
            order.save(update_fields=["order_date"])

            for _j in range(item_n):
                pid = rng.randint(1, product_max)
                qty = rng.randint(1, 3)
                unit = Decimal(str(rng.randint(50, 4000) * 1000))
                LegacyOrderItem.objects.create(
                    order=order,
                    product_id=pid,
                    product_name=f"Sản phẩm #{pid}",
                    quantity=qty,
                    unit_price=unit,
                    discount=Decimal("0"),
                )
                subtotal += unit * qty

            order.total_amount = subtotal + order.shipping_fee - order.discount_amount
            order.save(update_fields=["total_amount"])
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} legacy orders."))
