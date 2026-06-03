import uuid
from django.db import models
from .base import SoftDeleteModel

class ProductImage(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image_key = models.CharField(max_length=255)  # S3/MinIO object key
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['product', 'variant']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(product__isnull=False, variant__isnull=True) |
                    models.Q(product__isnull=True, variant__isnull=False)
                ),
                name='image_attached_to_exactly_one_owner'
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True, product__isnull=False),
                name="unique_primary_product_image"
            ),
            models.UniqueConstraint(
                fields=["variant"],
                condition=models.Q(is_primary=True, variant__isnull=False),
                name="unique_primary_variant_image"
            )
        ]

    def __str__(self):
        return self.image_key
