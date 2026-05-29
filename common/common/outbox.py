from django.db import models

class AbstractOutboxEvent(models.Model):
    aggregate_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default="PENDING") # PENDING, PUBLISHED, FAILED
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        abstract = True
