import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import SoftDeleteModel

class Review(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='reviews')
    user_id = models.UUIDField()
    order_id = models.UUIDField(null=True, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    verified_purchase = models.BooleanField(default=False)

    class Meta:
        unique_together = ('product', 'user_id')
        indexes = [models.Index(fields=['product', 'rating'])]

    def __str__(self):
        return f"Review for {self.product.name} by {self.user_id}"
