from django.db import models
from .supplier import Supplier


class POStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    RECEIVED = "received", "Received"
    CANCELLED = "cancelled", "Cancelled"


class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    admin_id = models.IntegerField(null=True, blank=True)   # ref → staff-service
    expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=POStatus.choices, default=POStatus.PENDING)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchase_orders"

    def __str__(self):
        return f"PO-{self.id} ({self.status})"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    book_id = models.IntegerField()           # ref → book-service
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "purchase_order_items"
