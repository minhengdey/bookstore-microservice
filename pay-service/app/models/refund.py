from django.db import models
from .payment import Payment


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    refund_date = models.DateTimeField(auto_now_add=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_reason = models.TextField(blank=True)
    transaction_type = models.CharField(max_length=50, default="refund")
    admin_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "refunds"
