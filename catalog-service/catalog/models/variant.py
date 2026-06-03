import uuid
from django.db import models
from .base import SoftDeleteModel

class ProductVariant(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=64, blank=True)
    attributes = models.JSONField(default=dict)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)  # kg
    length = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)  # cm
    width = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    height = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.sku}"
