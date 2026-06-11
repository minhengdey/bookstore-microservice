from django.db import models

class Cart(models.Model):
    customer_id = models.IntegerField(unique=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart(customer_id={self.customer_id})"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_id = models.IntegerField()
    variant_id = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField(default=1)
    # Unit price is optional/snapshot price. Order-service is the source of truth.
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "product_id")

    def __str__(self):
        return f"CartItem(product_id={self.product_id}, qty={self.quantity})"
