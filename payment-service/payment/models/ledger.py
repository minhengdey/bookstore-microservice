import uuid
from django.db import models
from .base import AuditBaseModel
from .intent import PaymentIntent

class PaymentTransaction(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20)
    provider_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    provider_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20)
    gateway_status = models.CharField(max_length=50, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
