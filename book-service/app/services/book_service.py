from app.repositories import BookRepository


class BookService:
    def __init__(self):
        self.repo = BookRepository()

    def list_books(self, search: str = None, status: str = None):
        if search:
            return self.repo.search(search)
        if status:
            return self.repo.get_by_status(status)
        return self.repo.get_all()

    def get_book(self, book_id: int):
        book = self.repo.get_by_id(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")
        return book

    def create_book(self, data: dict) -> object:
        author_ids = data.pop("author_ids", [])
        category_ids = data.pop("category_ids", [])
        genre_ids = data.pop("genre_ids", [])
        publisher_ids = data.pop("publisher_ids", [])
        images = data.pop("images", [])
        conditions = data.pop("conditions", [])
        languages = data.pop("language_names", [])

        book = self.repo.create(**data)

        for aid in author_ids:
            self.repo.add_author(book, aid)
        for cid in category_ids:
            self.repo.add_category(book, cid)
        for gid in genre_ids:
            self.repo.add_genre(book, gid)
        for pid in publisher_ids:
            self.repo.add_publisher(book, pid)
        for img in images:
            self.repo.add_image(book, img.get("image_url"), img.get("is_primary", False))
        for cond in conditions:
            self.repo.add_condition(book, **cond)
        for lang in languages:
            self.repo.add_language(book, lang)

        return self.repo.get_by_id(book.id)

    def update_book(self, book_id: int, data: dict):
        book = self.get_book(book_id)
        data.pop("author_ids", None)
        data.pop("category_ids", None)
        data.pop("genre_ids", None)
        data.pop("publisher_ids", None)
        return self.repo.update(book, **data)

    def delete_book(self, book_id: int):
        book = self.get_book(book_id)
        self.repo.delete(book)

    def decrease_stock(self, book_id: int, qty: int):
        book = self.get_book(book_id)
        if book.stock < qty:
            raise ValueError("Insufficient stock")
        return self.repo.decrease_stock(book, qty)
