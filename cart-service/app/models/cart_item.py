from django.db import models
from .cart import Cart


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    book_id = models.IntegerField()
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "book_id")

    def __str__(self):
        return f"CartItem(book_id={self.book_id}, qty={self.quantity})"
