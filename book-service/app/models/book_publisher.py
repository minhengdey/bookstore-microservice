from django.db import models
from .book import Book


class BookPublisher(models.Model):
    """Cross-service reference: publisher_id points to catalog-service Publisher."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_publishers")
    publisher_id = models.IntegerField()

    class Meta:
        db_table = "book_publishers"
        unique_together = ("book", "publisher_id")
