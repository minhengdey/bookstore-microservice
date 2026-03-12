"""
Tạo dữ liệu mẫu: RecommendationLog.
Giả định customer-service và book-service đã seed (customer_id 1,2,3; book_id 1-5).
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
            book_ids=[2, 3, 4],
            strategy="collaborative",
        )
        RecommendationLog.objects.create(
            customer_id=2,
            book_ids=[1, 3, 5],
            strategy="content_based",
        )
        RecommendationLog.objects.create(
            customer_id=3,
            book_ids=[1, 2, 4],
            strategy="collaborative",
        )

        self.stdout.write(self.style.SUCCESS("Created 3 recommendation logs."))
