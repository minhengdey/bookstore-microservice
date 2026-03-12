from django.db import models
from .payment_method import PaymentMethod


class CustomerPaymentMethod(models.Model):
    customer_id = models.IntegerField()    # ref → customer-service
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    account_number = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "customer_payment_methods"
