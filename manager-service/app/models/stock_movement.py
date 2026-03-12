from django.db import models
from .warehouse import Warehouse


class StockMovement(models.Model):
    book_id = models.IntegerField()
    from_warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="outgoing_movements"
    )
    to_warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="incoming_movements"
    )
    quantity = models.IntegerField()
    movement_date = models.DateTimeField(auto_now_add=True)
    transfer_date = models.DateTimeField(null=True, blank=True)
    admin_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "stock_movements"


class StockMovementLog(models.Model):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_movement_logs"


class StockTransfer(models.Model):
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="transfers_out")
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="transfers_in")
    book_id = models.IntegerField()
    quantity = models.IntegerField()
    transfer_date = models.DateTimeField(auto_now_add=True)
    admin_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default="pending")

    class Meta:
        db_table = "stock_transfers"
