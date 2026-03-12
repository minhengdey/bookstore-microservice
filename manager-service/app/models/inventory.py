from django.db import models
from .warehouse import Warehouse


class Inventory(models.Model):
    book_id = models.IntegerField()          # ref → book-service
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventories")
    stock_quantity = models.IntegerField(default=0)
    min_quantity = models.IntegerField(default=0)
    max_quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventories"
        unique_together = ("book_id", "warehouse")

    def __str__(self):
        return f"Inventory(book={self.book_id}, warehouse={self.warehouse_id}, qty={self.stock_quantity})"
