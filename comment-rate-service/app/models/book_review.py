from django.db import models


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class BookReview(models.Model):
    book_id = models.IntegerField()           # ref → book-service
    customer_id = models.IntegerField()       # ref → customer-service
    reviews_text = models.TextField(blank=True)
    rating = models.IntegerField()            # 1–5
    created_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)

    class Meta:
        db_table = "book_reviews"
        ordering = ["-created_date"]
        unique_together = ("book_id", "customer_id")

    def __str__(self):
        return f"Review(book={self.book_id}, customer={self.customer_id}, rating={self.rating})"
