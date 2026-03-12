from django.db import models
from .book import Book


class BookCondition(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="conditions")
    format = models.CharField(max_length=100)        # e.g. Hardcover, Paperback, eBook
    format_price = models.DecimalField(max_digits=10, decimal_places=2)
    book_condition = models.CharField(max_length=100) # e.g. New, Used, Like New

    class Meta:
        db_table = "book_conditions"
