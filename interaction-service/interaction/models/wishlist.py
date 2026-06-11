from django.db import models

class Wishlist(models.Model):
    customer_id = models.IntegerField()
    product_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlists"
        unique_together = ('customer_id', 'product_id')

    def __str__(self):
        return f"Wishlist(customer={self.customer_id}, product={self.product_id})"
