from django.db import models


class PaymentMethod(models.Model):
    method_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "payment_methods"

    def __str__(self):
        return self.method_name
