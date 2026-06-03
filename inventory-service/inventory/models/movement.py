import uuid
from django.db import models
from .base import AuditBaseModel

class InventoryMovement(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant_id = models.UUIDField()
    type = models.CharField(
        max_length=20,
        choices=[
            ('PURCHASE', 'PURCHASE'),
            ('RESERVE', 'RESERVE'),
            ('RELEASE', 'RELEASE'),
            ('CONFIRM', 'CONFIRM'),
            ('ADJUSTMENT', 'ADJUSTMENT'),
            ('RETURN', 'RETURN')
        ]
    )
    quantity = models.IntegerField()
    available_before = models.IntegerField()
    available_after = models.IntegerField()
    reserved_before = models.IntegerField()
    reserved_after = models.IntegerField()
    total_before = models.IntegerField()
    total_after = models.IntegerField()
    reference_id = models.UUIDField(null=True, blank=True)
