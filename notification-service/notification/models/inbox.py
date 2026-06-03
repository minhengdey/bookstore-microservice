from django.db import models
from .base import AuditBaseModel

class ProcessedEvent(AuditBaseModel):
    event_id = models.UUIDField(primary_key=True)
