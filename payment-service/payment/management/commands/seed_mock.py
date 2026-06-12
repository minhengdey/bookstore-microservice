"""
Seed payment methods và bản ghi thanh toán mẫu.
"""
import os
import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from payment.legacy_models import Payment, PaymentMethod, PaymentStatus, ShippingStatus


class Command(BaseCommand):
    help = "Seed mock payment methods and payment records"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--payments", type=int, default=int(os.getenv("MOCK_PAYMENT_COUNT", "200")))
        parser.add_argument("--order-max-id", type=int, default=int(os.getenv("MOCK_ORDER_COUNT", "250")))

    def handle(self, *args, **options):
        rng = random.Random(13)
        payment_count = max(10, int(options["payments"]))
        order_max = max(20, int(options["order_max_id"]))

        method, _ = PaymentMethod.objects.get_or_create(
            method_name="Thanh toán giả lập",
            defaults={
                "description": "Mô phỏng thanh toán (tự động thành công)",
                "is_active": True,
            },
        )
        PaymentMethod.objects.exclude(pk=method.pk).update(is_active=False)

        if options.get("clear"):
            Payment.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu payment."))

        if Payment.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE(
                f"Đã có {Payment.objects.count()} payments, bỏ qua (dùng --force --clear)."
            ))
            return

        statuses = [
            PaymentStatus.COMPLETED,
            PaymentStatus.COMPLETED,
            PaymentStatus.COMPLETED,
            PaymentStatus.PENDING,
            PaymentStatus.FAILED,
            PaymentStatus.REFUNDED,
        ]
        ship_statuses = [
            ShippingStatus.SHIPPED,
            ShippingStatus.PROCESSING,
            ShippingStatus.PENDING,
            ShippingStatus.FAILED,
        ]

        created = 0
        for order_id in range(1, order_max + 1):
            if Payment.objects.filter(order_id=order_id).exists():
                continue
            if created >= payment_count:
                break
            pay_status = rng.choice(statuses)
            ship_status = rng.choice(ship_statuses)
            if pay_status != PaymentStatus.COMPLETED:
                ship_status = ShippingStatus.PENDING

            Payment.objects.create(
                order_id=order_id,
                payment_amount=Decimal(str(rng.randint(150, 8500) * 1000)),
                payment_method=method,
                payment_status=pay_status,
                transaction_ref=f"MOCK-{order_id:06d}",
                shipping_status=ship_status,
                shipping_retry_count=1 if ship_status == ShippingStatus.FAILED else 0,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} payment records."))
