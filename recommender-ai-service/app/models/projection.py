from django.db import models
from .base import AuditBaseModel

class UserProjection(AuditBaseModel):
    user_id = models.UUIDField(primary_key=True)
    role = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    projection_version = models.BigIntegerField(default=0)

class ProductProjection(AuditBaseModel):
    product_id = models.UUIDField(primary_key=True)
    category_id = models.UUIDField(null=True, blank=True)
    brand_id = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    projection_version = models.BigIntegerField(default=0)
    
class UserSequenceEvent(AuditBaseModel):
    user_id = models.UUIDField()
    product_id = models.UUIDField()
    event_type = models.CharField(max_length=50)
    weight = models.FloatField(default=1.0)
    timestamp = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['user_id', '-timestamp'])
        ]
