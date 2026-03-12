"""
Tạo dữ liệu mẫu: BookReview.
Giả định customer-service và book-service đã seed (customer_id 1,2,3; book_id 1-5).
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from app.models import BookReview
from app.models.book_review import ReviewStatus


class Command(BaseCommand):
    help = "Seed mock data: book reviews and ratings"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            BookReview.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu comment-rate."))

        if BookReview.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu book review, bỏ qua seed."))
            return

        reviews = [
            (1, 1, "Sách hay, đáng đọc!", 5),
            (1, 2, "Rất cảm động.", 4),
            (2, 1, "Tác phẩm hay của Nguyễn Nhật Ánh.", 5),
            (2, 3, "Phù hợp thiếu nhi.", 4),
            (3, 1, "Câu chuyện ý nghĩa.", 5),
            (3, 2, "Đã đọc nhiều lần.", 5),
            (4, 2, "Rất thích phong cách Murakami.", 4),
            (5, 3, "Đáng suy ngẫm.", 4),
        ]
        for customer_id, book_id, text, rating in reviews:
            BookReview.objects.create(
                book_id=book_id,
                customer_id=customer_id,
                reviews_text=text,
                rating=rating,
                status=ReviewStatus.APPROVED,
            )

        self.stdout.write(self.style.SUCCESS(f"Created {len(reviews)} book reviews."))
