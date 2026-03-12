from django.db import models
from .payment_method import PaymentMethod


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    order_id = models.IntegerField(unique=True)   # ref → order-service
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, null=True, on_delete=models.SET_NULL)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_ref = models.CharField(max_length=255, blank=True)
    admin_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment(order={self.order_id}, {self.payment_status})"
