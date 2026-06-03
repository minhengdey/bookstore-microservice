import uuid
from django.db import models

class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_id = models.UUIDField()
    aggregate_type = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    message_id = models.UUIDField(unique=True)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'PENDING'), ('PUBLISHED', 'PUBLISHED'), ('FAILED', 'FAILED')],
        default='PENDING'
    )
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ProcessedMessage(models.Model):
    message_id = models.CharField(max_length=255, primary_key=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='SUCCESS')

class ProcessedWebhook(models.Model):
    provider_event_id = models.CharField(max_length=255, primary_key=True)
    signature_hash = models.CharField(max_length=255)
    received_at = models.DateTimeField(auto_now_add=True)
