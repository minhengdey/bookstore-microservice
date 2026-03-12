from django.db import models
from .book import Book


class BookAuthor(models.Model):
    """Cross-service reference: author_id points to catalog-service Author."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_authors")
    author_id = models.IntegerField()

    class Meta:
        db_table = "book_authors"
        unique_together = ("book", "author_id")
