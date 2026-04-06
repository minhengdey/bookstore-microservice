from django.db import models


class BehaviorEvent(models.Model):
    customer_id = models.IntegerField()
    book_id = models.IntegerField()
    action = models.CharField(max_length=50)
    action_weight = models.FloatField(default=1.0)
    event_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customer_behaviors"
        ordering = ["-event_time"]
