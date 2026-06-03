from rest_framework import serializers
from inventory.models import Inventory, InventoryMovement, ReservationBatch, StockReservation

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class ReserveStockItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

class ReserveStockRequestSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    correlation_id = serializers.UUIDField(required=False, allow_null=True)
    items = ReserveStockItemSerializer(many=True)

class AdjustStockRequestSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField()
    user_id = serializers.UUIDField(required=False, allow_null=True)

class PurchaseStockRequestSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    user_id = serializers.UUIDField(required=False, allow_null=True)
