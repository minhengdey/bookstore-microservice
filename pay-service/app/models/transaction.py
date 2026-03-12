from django.db import models


class Transaction(models.Model):
    order_id = models.IntegerField()       # ref → order-service
    refund_id = models.IntegerField(null=True, blank=True)
    created_name = models.CharField(max_length=255, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(max_length=50)  # payment | refund
    value = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, default="success")

    class Meta:
        db_table = "transactions"
