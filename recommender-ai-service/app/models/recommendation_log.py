from django.db import models


class RecommendationLog(models.Model):
    customer_id = models.IntegerField()
    book_ids = models.JSONField(default=list)     # list of recommended book IDs
    created_at = models.DateTimeField(auto_now_add=True)
    strategy = models.CharField(max_length=100, default="collaborative")

    class Meta:
        db_table = "recommendation_logs"
        ordering = ["-created_at"]
