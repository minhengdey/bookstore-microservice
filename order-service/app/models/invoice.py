from django.db import models
from .order import Order


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
