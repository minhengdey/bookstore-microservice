import uuid
from django.db import models
from .base import AuditBaseModel
from .order import Order

class OrderSaga(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='saga')
    correlation_id = models.UUIDField()
    current_step = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    last_error = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    timeout_at = models.DateTimeField(null=True, blank=True)
