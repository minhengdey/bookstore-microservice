from django.db import models
from .base import AuditBaseModel

class NotificationTemplate(AuditBaseModel):
    event_type = models.CharField(max_length=100)
    channel = models.CharField(max_length=20) # 'EMAIL', 'SMS', 'PUSH'
    locale = models.CharField(max_length=10, default="vi")
    template_version = models.IntegerField(default=1)
    subject_template = models.CharField(max_length=255, null=True, blank=True)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('event_type', 'channel', 'locale', 'template_version')
