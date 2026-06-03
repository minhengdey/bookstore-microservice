import uuid
from django.db import models
from .base import AuditBaseModel

class PaymentIntent(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(unique=True)
    correlation_id = models.UUIDField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    provider = models.CharField(max_length=50)
    provider_intent_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=[
            ('PENDING', 'PENDING'),
            ('PROCESSING', 'PROCESSING'),
            ('SUCCEEDED', 'SUCCEEDED'),
            ('FAILED', 'FAILED'),
            ('EXPIRED', 'EXPIRED'),
            ('REFUND_PENDING', 'REFUND_PENDING'),
            ('REFUNDED', 'REFUNDED')
        ],
        default='PENDING'
    )
    client_secret = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()
