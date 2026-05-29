from django.db import models


class BehaviorEvent(models.Model):
    customer_id = models.IntegerField()
    product_id = models.IntegerField()
    action = models.CharField(max_length=50)
    action_weight = models.FloatField(default=1.0)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    device = models.CharField(max_length=50, null=True, blank=True)
    persona = models.CharField(max_length=50, null=True, blank=True)
    event_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "customer_behaviors"
        ordering = ["-event_time"]
