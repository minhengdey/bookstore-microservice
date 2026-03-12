from django.db import models


class Cart(models.Model):
    customer_id = models.IntegerField(unique=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart(customer_id={self.customer_id})"
