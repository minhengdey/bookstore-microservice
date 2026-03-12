from django.db import models
from .book import Book


class BookImage(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="images")
    image_url = models.CharField(max_length=1000)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "book_images"

    def __str__(self):
        return f"Image for {self.book.title}"
