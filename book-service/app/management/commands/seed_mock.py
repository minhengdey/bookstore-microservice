"""
Tạo dữ liệu mẫu: Book, BookAuthor, BookCategory, BookGenre, BookPublisher, BookImage, BookCondition, BookLanguage.
Giả định catalog-service đã seed (author_id 1,2,3; category 1-4; genre 1-4; publisher 1-3).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection
from app.models import (
    Book, BookAuthor, BookCategory, BookGenre, BookPublisher,
    BookImage, BookCondition, BookLanguage,
)
from app.models.book import BookStatus


class Command(BaseCommand):
    help = "Seed mock data: books and book relations"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")
        parser.add_argument("--repair", action="store_true", help="Bổ sung dữ liệu thiếu cho sách hiện có")

    def _repair_existing_books(self):
        books = Book.objects.all().order_by("id")
        if not books.exists():
            self.stdout.write(self.style.WARNING("Không có sách để repair."))
            return

        total_authors = 20
        total_categories = 18
        total_genres = 78
        total_publishers = 72

        repaired = 0
        for i, book in enumerate(books):
            changed = False
            if not (book.description or "").strip():
                book.description = (
                    f"Sách {book.title} tập trung vào phát triển bản thân, "
                    "kết hợp góc nhìn thực tế và ví dụ dễ áp dụng."
                )
                changed = True
            if not book.publication_year:
                book.publication_year = 2018 + (i % 7)
                changed = True
            if not book.page_count:
                book.page_count = 180 + (i % 10) * 12
                changed = True
            if changed:
                book.save(update_fields=["description", "publication_year", "page_count", "updated_date"])

            if not book.book_authors.exists():
                BookAuthor.objects.create(book=book, author_id=(i % total_authors) + 1)
                changed = True
            if not book.book_categories.exists():
                BookCategory.objects.create(book=book, category_id=(i % total_categories) + 1)
                changed = True
            if not book.book_genres.exists():
                BookGenre.objects.create(book=book, genre_id=(i % total_genres) + 1)
                changed = True
            if not book.book_publishers.exists():
                BookPublisher.objects.create(book=book, publisher_id=(i % total_publishers) + 1)
                changed = True
            if not book.images.exists():
                BookImage.objects.create(book=book, image_url=f"/static/books/{book.id}.jpg", is_primary=True)
                changed = True
            if not book.conditions.exists():
                BookCondition.objects.create(
                    book=book,
                    format="Bìa mềm",
                    format_price=book.sale_price,
                    book_condition="Mới",
                )
                changed = True
            if not book.languages.exists():
                BookLanguage.objects.create(book=book, language_name="Tiếng Việt")
                changed = True

            if changed:
                repaired += 1

        self.stdout.write(self.style.SUCCESS(f"Repair xong. Đã cập nhật {repaired}/{books.count()} sách."))

    def handle(self, *args, **options):
        if options.get("clear"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "TRUNCATE TABLE book_languages, book_conditions, book_images, "
                    "book_publishers, book_genres, book_categories, book_authors, books "
                    "RESTART IDENTITY CASCADE;"
                )
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu book."))

        if Book.objects.exists():
            if options.get("repair"):
                self._repair_existing_books()
            else:
                self.stdout.write(self.style.NOTICE("Đã có dữ liệu book, bỏ qua seed. Dùng --repair để bổ sung dữ liệu thiếu."))
            return

        cum_tu_1 = [
            "Mùa gió", "Dòng sông", "Con đường", "Mảnh sân", "Phố nhỏ",
            "Vệt nắng", "Cánh đồng", "Bến xe", "Ánh trăng", "Tiếng mưa",
        ]
        cum_tu_2 = [
            "tháng năm", "đợi chờ", "tuổi trẻ", "quê nhà", "bình yên",
            "xa xôi", "kỷ niệm", "học trò", "mơ ước", "đổi thay",
        ]
        chu_de = [
            "học cách sống tử tế mỗi ngày",
            "hành trình trưởng thành của người trẻ",
            "bí quyết quản lý thời gian hiệu quả",
            "xây dựng thói quen tích cực bền vững",
            "nuôi dưỡng lòng biết ơn và yêu thương",
            "vượt qua áp lực học tập và công việc",
            "thực hành giao tiếp chân thành",
            "khơi dậy cảm hứng sáng tạo trong đời sống",
            "giữ lửa đam mê học tập lâu dài",
            "thấu hiểu bản thân trong giai đoạn chuyển mình",
        ]

        books_data = []
        total_books = 80
        for i in range(total_books):
            tieu_de = f"{cum_tu_1[i % len(cum_tu_1)]} {cum_tu_2[(i // len(cum_tu_1)) % len(cum_tu_2)]}"
            mo_ta = (
                f"Cuốn sách chia sẻ về {chu_de[i % len(chu_de)]}, "
                f"được viết với ngôn ngữ gần gũi và giàu cảm xúc."
            )
            list_price = Decimal(str(68000 + (i % 12) * 7000))
            sale_price = (list_price * Decimal("0.9")).quantize(Decimal("1"))

            books_data.append({
                "title": f"{tieu_de} - Tập {i + 1}",
                "isbn": f"978604{2000000 + i}",
                "description": mo_ta,
                "publication_year": 2016 + (i % 10),
                "page_count": 160 + (i % 14) * 16,
                "list_price": list_price,
                "sale_price": sale_price,
                "stock": 30 + (i % 40),
                "status": BookStatus.ACTIVE,
            })

        created_books = []
        total_authors = 20
        total_categories = 18
        total_genres = 78
        total_publishers = 72

        for i, b in enumerate(books_data):
            book = Book.objects.create(**b)
            created_books.append(book)

            author_id = (i % total_authors) + 1
            BookAuthor.objects.create(book=book, author_id=author_id)
            BookCategory.objects.create(book=book, category_id=(i % total_categories) + 1)
            BookGenre.objects.create(book=book, genre_id=(i % total_genres) + 1)
            BookPublisher.objects.create(book=book, publisher_id=(i % total_publishers) + 1)
            BookImage.objects.create(book=book, image_url=f"/static/books/{book.id}.jpg", is_primary=True)
            BookCondition.objects.create(
                book=book,
                format="Bìa mềm",
                format_price=book.sale_price,
                book_condition="Mới",
            )
            BookLanguage.objects.create(book=book, language_name="Tiếng Việt")

        self.stdout.write(self.style.SUCCESS(f"Created {len(created_books)} books with authors/categories/genres/publishers."))
