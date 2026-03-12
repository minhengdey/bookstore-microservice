from django.db import models
from .book import Book


class BookCategory(models.Model):
    """Cross-service reference: category_id points to catalog-service Category."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_categories")
    category_id = models.IntegerField()

    class Meta:
        db_table = "book_categories"
        unique_together = ("book", "category_id")
