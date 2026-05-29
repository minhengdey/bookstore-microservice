from django.db import models

class PaymentMethod(models.Model):
    method_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "payment_methods"

    def __str__(self):
        return self.method_name

class CustomerPaymentMethod(models.Model):
    customer_id = models.IntegerField()
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    account_number = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "customer_payment_methods"

class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"

class ShippingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    FAILED = "failed", "Failed"

class Payment(models.Model):
    order_id = models.IntegerField(unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, null=True, on_delete=models.SET_NULL)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_ref = models.CharField(max_length=255, blank=True)
    admin_id = models.IntegerField(null=True, blank=True)
    
    # Shipping Resilience
    shipping_status = models.CharField(max_length=20, choices=ShippingStatus.choices, default=ShippingStatus.PENDING)
    shipping_failure_reason = models.TextField(blank=True, null=True)
    shipping_retry_count = models.IntegerField(default=0)

    class Meta:
        db_table = "payments"
        
from common.outbox import AbstractOutboxEvent

class PaymentOutbox(AbstractOutboxEvent):
    class Meta:
        db_table = "payment_outbox"

    def __str__(self):
        return f"Payment(order={self.order_id}, {self.payment_status}, ship={self.shipping_status})"

class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    refund_date = models.DateTimeField(auto_now_add=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_reason = models.TextField(blank=True)
    transaction_type = models.CharField(max_length=50, default="refund")
    admin_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "refunds"

class Transaction(models.Model):
    order_id = models.IntegerField()
    refund_id = models.IntegerField(null=True, blank=True)
    created_name = models.CharField(max_length=255, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(max_length=50)  # payment | refund
    value = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, default="success")

    class Meta:
        db_table = "transactions"
