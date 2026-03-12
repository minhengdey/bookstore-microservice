from django.db import models
from .book import Book


class BookGenre(models.Model):
    """Cross-service reference: genre_id points to catalog-service Genre."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_genres")
    genre_id = models.IntegerField()

    class Meta:
        db_table = "book_genres"
        unique_together = ("book", "genre_id")
