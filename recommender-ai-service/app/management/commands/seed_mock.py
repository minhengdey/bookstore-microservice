"""
Tạo dữ liệu mẫu: RecommendationLog.
Giả định customer-service đã seed (customer_id 1,2,3) và product catalog đã có các product_id 1-12.
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from app.models import RecommendationLog


class Command(BaseCommand):
    help = "Seed mock data: recommendation logs"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            RecommendationLog.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu recommender."))

        if RecommendationLog.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu recommendation log, bỏ qua seed."))
            return

        RecommendationLog.objects.create(
            customer_id=1,
            product_ids=[4, 6, 11],
            strategy="collaborative",
        )
        RecommendationLog.objects.create(
            customer_id=2,
            product_ids=[1, 9, 10],
            strategy="content_based",
        )
        RecommendationLog.objects.create(
            customer_id=3,
            product_ids=[8, 12, 7],
            strategy="hybrid",
        )
        RecommendationLog.objects.create(
            customer_id=1,
            product_ids=[2, 5, 7],
            strategy="trending",
        )

        self.stdout.write(self.style.SUCCESS("Created 4 recommendation logs."))
