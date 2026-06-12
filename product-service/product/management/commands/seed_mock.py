"""
Tạo dữ liệu mẫu lớn: Category, Brand, Product (mặc định >= 320 SP).
Chạy: python manage.py seed_mock
      python manage.py seed_mock --clear
      python manage.py seed_mock --clear --force --count 320
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from common.mock_catalog import CATEGORIES, DEFAULT_PRODUCT_COUNT, generate_brands, generate_products
from product.models import Brand, Category, Product, StockReservationLog


class Command(BaseCommand):
    help = "Seed large mock catalog (categories, brands, products)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu product trước khi seed")
        parser.add_argument("--force", action="store_true", help="Seed lại kể cả khi đã có dữ liệu")
        parser.add_argument(
            "--count",
            type=int,
            default=int(os.getenv("MOCK_PRODUCT_COUNT", str(DEFAULT_PRODUCT_COUNT))),
            help="Số lượng sản phẩm cần tạo",
        )

    def handle(self, *args, **options):
        target = max(50, int(options["count"]))
        current = Product.objects.count()

        if not options.get("clear") and not options.get("force"):
            if current >= target:
                self.stdout.write(self.style.NOTICE(
                    f"Đã có {current} sản phẩm (>= {target}), bỏ qua seed."
                ))
                return
            if current > 0:
                self.stdout.write(self.style.WARNING(
                    f"Catalog nhỏ ({current} < {target}) — tự động nâng cấp lên {target} SP."
                ))
                options["clear"] = True

        if options.get("clear"):
            StockReservationLog.objects.all().delete()
            Product.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu product."))

        if Product.objects.exists() and not options.get("force") and not options.get("clear"):
            total = Product.objects.count()
            self.stdout.write(self.style.NOTICE(f"Đã có {total} sản phẩm, bỏ qua seed (dùng --force --clear)."))
            return

        with transaction.atomic():
            cat_map = {}
            for idx, (name, description, _slug) in enumerate(CATEGORIES, start=1):
                cat, _ = Category.objects.update_or_create(
                    id=idx,
                    defaults={"name": name, "description": description},
                )
                cat_map[name] = cat

            brand_map = {}
            for raw in generate_brands():
                brand, _ = Brand.objects.get_or_create(
                    name=raw["name"],
                    defaults={"description": raw["description"]},
                )
                brand_map[raw["name"]] = brand

            created = 0
            for raw in generate_products(target_count=target):
                cat = cat_map.get(raw["category_name"])
                if not cat:
                    continue
                brand = brand_map.get(raw["brand_name"])
                _, was_created = Product.objects.update_or_create(
                    sku=raw["sku"],
                    defaults={
                        "name": raw["name"],
                        "category": cat,
                        "brand": brand,
                        "price": raw["price"],
                        "currency": "VND",
                        "image_url": raw["image_url"],
                        "attributes": raw["attributes"],
                        "description": raw["description"],
                        "status": raw["status"],
                        "stock": raw["stock"],
                    },
                )
                if was_created:
                    created += 1

        total = Product.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Catalog ready: {Category.objects.count()} categories, "
            f"{Brand.objects.count()} brands, {total} products ({created} newly created)."
        ))
