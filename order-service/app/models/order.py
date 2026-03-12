from django.db import models


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class Order(models.Model):
    customer_id = models.IntegerField()    # ref → customer-service
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
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
    book_id = models.IntegerField()         # ref → book-service
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "order_items"

    @property
    def subtotal(self):
        return (self.unit_price - self.discount) * self.quantity


class OrderDiscount(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_discounts")
    discount_id = models.IntegerField()     # ref to Discount in same DB
    applied_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_discounts"
