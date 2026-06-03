from django.db import models
from .base import AuditBaseModel

class UserContactProjection(AuditBaseModel):
    user_id = models.UUIDField(primary_key=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    push_token = models.CharField(max_length=255, null=True, blank=True)
    preferences = models.JSONField(default=dict)
