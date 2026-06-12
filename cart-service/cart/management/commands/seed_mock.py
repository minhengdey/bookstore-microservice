"""
Seed giỏ hàng mẫu cho nhiều khách hàng.
Chạy: python manage.py seed_mock --clear --force
"""
import os
import random

from decimal import Decimal
from django.core.management.base import BaseCommand
from cart.models import Cart, CartItem


class Command(BaseCommand):
    help = "Seed mock carts and cart items"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
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
        customer_count = max(3, int(options["customers"]))
        product_max = max(24, int(options["product_max_id"]))
        rng = random.Random(42)

        if options.get("clear"):
            CartItem.objects.all().delete()
            Cart.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu cart."))

        if Cart.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE(f"Đã có {Cart.objects.count()} cart, bỏ qua (dùng --force)."))
            return

        created_carts = 0
        created_items = 0
        for cid in range(1, customer_count + 1):
            cart, _ = Cart.objects.get_or_create(customer_id=cid)
            if cart.items.exists() and not options.get("force"):
                continue
            if options.get("force"):
                cart.items.all().delete()

            item_count = rng.randint(1, 5)
            product_ids = rng.sample(range(1, product_max + 1), k=min(item_count, product_max))
            for pid in product_ids:
                unit_price = Decimal(str(rng.randint(50, 3500) * 1000))
                CartItem.objects.create(
                    cart=cart,
                    product_id=pid,
                    quantity=rng.randint(1, 3),
                    unit_price=unit_price,
                )
                created_items += 1
            created_carts += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded carts for {created_carts} customers with {created_items} items."
        ))
