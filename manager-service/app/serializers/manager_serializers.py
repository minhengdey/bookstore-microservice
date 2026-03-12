from rest_framework import serializers
from app.models import (
    Warehouse, WarehouseLocation, Inventory,
    Supplier, PurchaseOrder, PurchaseOrderItem, StockMovement,
)


class WarehouseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseLocation
        fields = "__all__"


class WarehouseSerializer(serializers.ModelSerializer):
    locations = WarehouseLocationSerializer(many=True, read_only=True)
    class Meta:
        model = Warehouse
        fields = "__all__"


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "book_id", "quantity", "unit_price"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.supplier_name", read_only=True)
    class Meta:
        model = PurchaseOrder
        fields = "__all__"


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"
