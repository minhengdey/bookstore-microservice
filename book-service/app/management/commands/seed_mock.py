"""
Tạo dữ liệu mẫu: Book, BookAuthor, BookCategory, BookGenre, BookPublisher, BookImage, BookCondition, BookLanguage.
Giả định catalog-service đã seed (author_id 1,2,3; category 1-4; genre 1-4; publisher 1-3).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from app.models import (
    Book, BookAuthor, BookCategory, BookGenre, BookPublisher,
    BookImage, BookCondition, BookLanguage,
)
from app.models.book import BookStatus


class Command(BaseCommand):
    help = "Seed mock data: books and book relations"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            for M in [BookLanguage, BookCondition, BookImage, BookAuthor, BookCategory, BookGenre, BookPublisher, Book]:
                M.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu book."))

        if Book.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu book, bỏ qua seed."))
            return

        books_data = [
            {"title": "Cho tôi xin một vé đi tuổi thơ", "isbn": "9786041110910", "list_price": Decimal("80000"), "sale_price": Decimal("72000"), "stock": 100},
            {"title": "Mắt biếc", "isbn": "9786041110921", "list_price": Decimal("75000"), "sale_price": Decimal("68000"), "stock": 80},
            {"title": "Nhà giả kim", "isbn": "9786041110932", "list_price": Decimal("99000"), "sale_price": Decimal("89000"), "stock": 50},
            {"title": "Rừng Na Uy", "isbn": "9786041110943", "list_price": Decimal("120000"), "sale_price": Decimal("108000"), "stock": 40},
            {"title": "Điều kỳ diệu của tiệm tạp hóa Namiya", "isbn": "9786041110954", "list_price": Decimal("110000"), "sale_price": Decimal("99000"), "stock": 30},
        ]
        for b in books_data:
            b.setdefault("description", "")
            b.setdefault("publication_year", 2020)
            b.setdefault("page_count", 250)
            b.setdefault("status", BookStatus.ACTIVE)

        created_books = []
        for i, b in enumerate(books_data):
            book = Book.objects.create(**b)
            created_books.append(book)
            # author_id: 1=Nguyễn Nhật Ánh, 2=Paulo Coelho, 3=Murakami
            author_id = 1 if i < 2 else (2 if i == 2 else 3)
            BookAuthor.objects.create(book=book, author_id=author_id)
            BookCategory.objects.create(book=book, category_id=(i % 4) + 1)
            BookGenre.objects.create(book=book, genre_id=(i % 4) + 1)
            BookPublisher.objects.create(book=book, publisher_id=(i % 3) + 1)
            BookImage.objects.create(book=book, image_url=f"/static/books/{book.id}.jpg", is_primary=True)
            BookCondition.objects.create(book=book, format="Paperback", format_price=book.sale_price, book_condition="New")
            BookLanguage.objects.create(book=book, language_name="Tiếng Việt" if i < 2 else "Tiếng Việt")

        self.stdout.write(self.style.SUCCESS(f"Created {len(created_books)} books with authors/categories/genres/publishers."))
