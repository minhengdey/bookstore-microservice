from django.core.management.base import BaseCommand
from product.services import ProductService


class Command(BaseCommand):
    help = "Đồng bộ flash sale từ promotion-service vào bảng products"

    def handle(self, *args, **options):
        result = ProductService().sync_flash_sales_from_promotion()
        self.stdout.write(self.style.SUCCESS(
            f"Flash sale sync done: {result['synced']} updated, {result['cleared']} cleared."
        ))
