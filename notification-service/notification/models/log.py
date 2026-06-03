import uuid
from django.db import models
from .base import AuditBaseModel

class NotificationLog(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.CharField(max_length=255)
    channel = models.CharField(max_length=20)
    event_id = models.CharField(max_length=255)
    correlation_id = models.CharField(max_length=255)
    
    subject = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    payload_snapshot = models.JSONField(default=dict)
    template_version = models.IntegerField(default=1)
    
    provider_used = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, 
        choices=[
            ('QUEUED', 'QUEUED'),
            ('PROCESSING', 'PROCESSING'),
            ('SENT', 'SENT'),
            ('FAILED', 'FAILED'),
            ('RETRYING', 'RETRYING')
        ],
        default='QUEUED'
    )
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
