import uuid
from django.db import models

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_id = models.UUIDField()
    aggregate_type = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    actor_id = models.UUIDField(null=True, blank=True)
    actor_type = models.CharField(max_length=100, null=True, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    trace_id = models.CharField(max_length=32, null=True, blank=True)
    span_id = models.CharField(max_length=16, null=True, blank=True)
    payload_before = models.JSONField(null=True, blank=True)
    payload_after = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['aggregate_id']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['request_id']),
            models.Index(fields=['trace_id']),
            models.Index(fields=['created_at']),
        ]
