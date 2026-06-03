import uuid
from django.db import models
from .base import AuditBaseModel

class InteractionEvent(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True) # Nullable for guest users
    anonymous_id = models.UUIDField(null=True, blank=True) # For tracking pre-login behavior
    session_id = models.UUIDField()
    correlation_id = models.UUIDField(null=True, blank=True)
    product_id = models.UUIDField()
    event_type = models.CharField(max_length=50) # 'VIEW', 'CLICK', 'SEARCH', 'ADD_TO_CART', 'PURCHASE', etc.
    weight = models.FloatField()
    source = models.CharField(max_length=30, default="WEB")
    metadata = models.JSONField(default=dict, blank=True) # Device, platform, category, etc.
