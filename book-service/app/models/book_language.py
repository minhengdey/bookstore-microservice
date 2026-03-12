from django.db import models
from .book import Book


class BookLanguage(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="languages")
    language_name = models.CharField(max_length=100)

    class Meta:
        db_table = "book_languages"
        unique_together = ("book", "language_name")
