from django.db import models


class Warehouse(models.Model):
    warehouse_name = models.CharField(max_length=255)
    warehouse_code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    manager_id = models.IntegerField(null=True, blank=True)  # ref → staff-service
    capacity = models.IntegerField(default=0)

    class Meta:
        db_table = "warehouses"

    def __str__(self):
        return f"{self.warehouse_name} ({self.warehouse_code})"


class WarehouseLocation(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="locations")
    location_code = models.CharField(max_length=50)
    location_name = models.CharField(max_length=255, blank=True)
    row_number = models.CharField(max_length=10, blank=True)
    column_number = models.CharField(max_length=10, blank=True)
    floor_number = models.CharField(max_length=10, blank=True)
    capacity = models.IntegerField(default=0)

    class Meta:
        db_table = "warehouse_locations"
        unique_together = ("warehouse", "location_code")
