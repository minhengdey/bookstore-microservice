import uuid
from django.db import models

class OutboxEvent(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('PUBLISHED', 'PUBLISHED'),
        ('FAILED', 'FAILED'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_id = models.UUIDField()
    aggregate_type = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    message_id = models.UUIDField(unique=True)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
        ]

class ProcessedMessage(models.Model):
    message_id = models.UUIDField(primary_key=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['processed_at']),
        ]
