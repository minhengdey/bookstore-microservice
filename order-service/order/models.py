from django.db import models

class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    PENDING_PAYMENT = "pending_payment", "Pending Payment"
    PAID = "paid", "Paid"
    FAILED_PAYMENT = "failed_payment", "Failed Payment"

class Order(models.Model):
    customer_id = models.IntegerField()
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING_PAYMENT)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    admin_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order-{self.id} ({self.status})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.IntegerField()
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "order_items"

    @property
    def subtotal(self):
        return (self.unit_price - self.discount) * self.quantity

class Discount(models.Model):
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

class OrderDiscount(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_discounts")
    discount_id = models.IntegerField()
    applied_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_discounts"

class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"

class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
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

class Coupon(models.Model):
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

class OrderOutbox(AbstractOutboxEvent):
    class Meta:
        db_table = "order_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
