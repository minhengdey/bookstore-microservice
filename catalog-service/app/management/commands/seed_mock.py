"""
Tạo dữ liệu mẫu: Author, Category, Genre, Publisher.
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from app.models import Author, Category, Genre, Publisher


class Command(BaseCommand):
    help = "Seed mock data: authors, categories, genres, publishers"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            for M in [Author, Category, Genre, Publisher]:
                M.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu catalog."))

        if Author.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu catalog, bỏ qua seed."))
            return

        authors = [
            {"author_name": "Nguyễn Nhật Ánh", "biography": "Nhà văn Việt Nam", "birth_year": 1955},
            {"author_name": "Paulo Coelho", "biography": "Nhà văn Brazil", "birth_year": 1947},
            {"author_name": "Haruki Murakami", "biography": "Nhà văn Nhật Bản", "birth_year": 1949},
        ]
        for a in authors:
            Author.objects.create(**a)

        cat_goc = Category.objects.create(category_name="Sách gốc", description="Sách không dịch")
        Category.objects.create(category_name="Sách dịch", parent_category=cat_goc, description="Sách dịch")
        Category.objects.create(category_name="Sách thiếu nhi", description="Cho trẻ em")
        Category.objects.create(category_name="Sách văn học", description="Văn học trong nước và nước ngoài")

        genres = [
            {"genre_name": "Tiểu thuyết", "description": "Tiểu thuyết"},
            {"genre_name": "Truyện ngắn", "description": "Truyện ngắn"},
            {"genre_name": "Kỹ năng sống", "description": "Self-help"},
            {"genre_name": "Kinh doanh", "description": "Sách kinh doanh"},
        ]
        for g in genres:
            Genre.objects.create(**g)

        publishers = [
            {"publisher_name": "NXB Trẻ", "contact_name": "Phòng kinh doanh", "phone": "02839316266", "address": "TP.HCM"},
            {"publisher_name": "NXB Kim Đồng", "contact_name": "Liên hệ", "phone": "02438221304", "address": "Hà Nội"},
            {"publisher_name": "NXB Hội Nhà văn", "contact_name": "", "phone": "", "address": "Hà Nội"},
        ]
        for p in publishers:
            Publisher.objects.create(**p)

        self.stdout.write(self.style.SUCCESS(
            f"Created: {Author.objects.count()} authors, {Category.objects.count()} categories, "
            f"{Genre.objects.count()} genres, {Publisher.objects.count()} publishers"
        ))
