from rest_framework import serializers
from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "cart", "product_id", "quantity", "unit_price", "line_total"]
        read_only_fields = ["cart"]

    def get_line_total(self, obj):
        return float(obj.unit_price * obj.quantity)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ["id", "customer_id", "created_date", "items", "total_price"]

    def get_total_price(self, obj):
        return float(sum(item.unit_price * item.quantity for item in obj.items.all()))
