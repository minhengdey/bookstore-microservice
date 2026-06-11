from django.db import models

class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
    PAID = "PAID", "Paid"
    PROCESSING = "PROCESSING", "Processing"
    SHIPPING = "SHIPPING", "Shipping"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    RETURN_REQUESTED = "RETURN_REQUESTED", "Return Requested"
    RETURNED = "RETURNED", "Returned"
    REFUNDED = "REFUNDED", "Refunded"

class LegacyOrder(models.Model):
    customer_id = models.IntegerField()
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=OrderStatus.choices, default=OrderStatus.PENDING_PAYMENT)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Snapshots
    address_id = models.IntegerField(null=True, blank=True)
    shipping_address_snapshot = models.JSONField(null=True, blank=True)
    voucher_code = models.CharField(max_length=50, blank=True)
    
    admin_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order-{self.id} ({self.status})"

class LegacyOrderItem(models.Model):
    order = models.ForeignKey(LegacyOrder, on_delete=models.CASCADE, related_name="items")
    product_id = models.IntegerField()
    variant_id = models.IntegerField(null=True, blank=True)
    product_name = models.CharField(max_length=255, blank=True)
    variant_name = models.CharField(max_length=255, blank=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "order_items"

    @property
    def subtotal(self):
        return (self.unit_price - self.discount) * self.quantity

class LegacyDiscount(models.Model):
    discount_code = models.CharField(max_length=50, unique=True)
    discount_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discounts"

    def __str__(self):
        return f"{self.discount_code} ({self.discount_value}{'%' if self.is_percentage else ''})"

class LegacyOrderDiscount(models.Model):
    order = models.ForeignKey(LegacyOrder, on_delete=models.CASCADE, related_name="order_discounts")
    discount_id = models.IntegerField()
    applied_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_discounts"

class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"

class LegacyInvoice(models.Model):
    order = models.OneToOneField(LegacyOrder, on_delete=models.CASCADE, related_name="invoice")
    created_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    admin_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "invoices"

class CouponStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    USED = "used", "Used"
    EXPIRED = "expired", "Expired"

class LegacyCoupon(models.Model):
    customer_id = models.IntegerField()
    order_id = models.IntegerField(null=True, blank=True)
    coupon_code = models.CharField(max_length=50, unique=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=True)
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=CouponStatus.choices, default=CouponStatus.ACTIVE)

    class Meta:
        db_table = "coupons"

from common.outbox import AbstractOutboxEvent

class LegacyOrderOutbox(AbstractOutboxEvent):
    class Meta:
        db_table = "order_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
