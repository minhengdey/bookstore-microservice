from rest_framework import serializers
from order.models import Order, OrderItem, OrderSaga, OrderStatusHistory

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ('order',)

class OrderSagaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderSaga
        fields = '__all__'

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    saga = OrderSagaSerializer(read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

class CheckoutRequestSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    shipping_address = serializers.JSONField()

class CartItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
