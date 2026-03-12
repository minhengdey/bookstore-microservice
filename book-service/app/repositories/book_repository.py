from app.models import (
    Book, BookImage, BookAuthor, BookCategory,
    BookGenre, BookPublisher, BookCondition, BookLanguage,
)


class BookRepository:
    def get_all(self):
        return Book.objects.prefetch_related(
            "images", "book_authors", "book_categories",
            "book_genres", "book_publishers", "conditions", "languages"
        ).all()

    def get_by_id(self, pk):
        return Book.objects.prefetch_related(
            "images", "book_authors", "book_categories",
            "book_genres", "book_publishers", "conditions", "languages"
        ).filter(pk=pk).first()

    def search(self, query: str):
        return Book.objects.filter(title__icontains=query)

    def get_by_status(self, status: str):
        return Book.objects.filter(status=status)

    def create(self, **kwargs) -> Book:
        return Book.objects.create(**kwargs)

    def update(self, book: Book, **kwargs) -> Book:
        for field, value in kwargs.items():
            setattr(book, field, value)
        book.save()
        return book

    def delete(self, book: Book) -> None:
        book.delete()

    # ── Relations ─────────────────────────────────────────────────────────────

    def add_author(self, book: Book, author_id: int):
        return BookAuthor.objects.get_or_create(book=book, author_id=author_id)[0]

    def add_category(self, book: Book, category_id: int):
        return BookCategory.objects.get_or_create(book=book, category_id=category_id)[0]

    def add_genre(self, book: Book, genre_id: int):
        return BookGenre.objects.get_or_create(book=book, genre_id=genre_id)[0]

    def add_publisher(self, book: Book, publisher_id: int):
        return BookPublisher.objects.get_or_create(book=book, publisher_id=publisher_id)[0]

    def add_image(self, book: Book, image_url: str, is_primary: bool = False):
        if is_primary:
            BookImage.objects.filter(book=book).update(is_primary=False)
        return BookImage.objects.create(book=book, image_url=image_url, is_primary=is_primary)

    def add_condition(self, book: Book, **kwargs):
        return BookCondition.objects.create(book=book, **kwargs)

    def add_language(self, book: Book, language_name: str):
        return BookLanguage.objects.get_or_create(book=book, language_name=language_name)[0]

    def decrease_stock(self, book: Book, qty: int) -> Book:
        book.stock = max(0, book.stock - qty)
        book.save(update_fields=["stock"])
        return book
