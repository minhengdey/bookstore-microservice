import uuid
from django.db import models
from .base import AuditBaseModel

class ReservationBatch(AuditBaseModel):
    batch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(unique=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'PENDING'), ('CONFIRMED', 'CONFIRMED'), 
                 ('RELEASED', 'RELEASED'), ('EXPIRED', 'EXPIRED')]
    )
    expires_at = models.DateTimeField()

class StockReservation(AuditBaseModel):
    reservation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ReservationBatch, on_delete=models.CASCADE, related_name='items')
    variant_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'PENDING'), ('CONFIRMED', 'CONFIRMED'), 
                 ('RELEASED', 'RELEASED'), ('EXPIRED', 'EXPIRED')]
    )
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "variant_id"],
                condition=models.Q(status="PENDING"),
                name="unique_pending_reservation_per_batch"
            )
        ]
