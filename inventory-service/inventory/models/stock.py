from django.db import models
from .base import AuditBaseModel

class Inventory(AuditBaseModel):
    variant_id = models.UUIDField(primary_key=True)
    total_stock = models.IntegerField(default=0)
    available_stock = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)
    version = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
