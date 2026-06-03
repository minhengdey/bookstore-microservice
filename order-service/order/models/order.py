import uuid
from django.db import models
from .base import AuditBaseModel

ORDER_STATUS = [
    ('DRAFT', 'DRAFT'),
    ('RESERVING_STOCK', 'RESERVING_STOCK'),
    ('STOCK_RESERVED', 'STOCK_RESERVED'),
    ('PAYMENT_PENDING', 'PAYMENT_PENDING'),
    ('PAYMENT_PROCESSING', 'PAYMENT_PROCESSING'),
    ('WAITING_INVENTORY_CONFIRM', 'WAITING_INVENTORY_CONFIRM'),
    ('COMPLETED', 'COMPLETED'),
    ('PAYMENT_FAILED', 'PAYMENT_FAILED'),
    ('CANCELLING', 'CANCELLING'),
    ('CANCELLED', 'CANCELLED'),
    ('REFUND_PENDING', 'REFUND_PENDING'),
    ('REFUNDED', 'REFUNDED')
]

class Order(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    correlation_id = models.UUIDField(default=uuid.uuid4)
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default='DRAFT')
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    promotion_id = models.UUIDField(null=True, blank=True)
    promotion_code = models.CharField(max_length=50, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    payment_id = models.UUIDField(null=True, blank=True)
    payment_provider = models.CharField(max_length=50, null=True, blank=True)
    
    shipping_address = models.JSONField()

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id = models.UUIDField()
    variant_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    product_name = models.CharField(max_length=255)
    variant_sku = models.CharField(max_length=100)
    variant_attributes = models.JSONField(default=dict)
