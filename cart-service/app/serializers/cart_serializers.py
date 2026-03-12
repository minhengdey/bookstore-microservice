from rest_framework import serializers
from app.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["id", "book_id", "quantity", "unit_price"]
        read_only_fields = ["id"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "customer_id", "created_date", "items", "total_price"]
        read_only_fields = ["id", "created_date"]

    def get_total_price(self, obj):
        return sum(item.unit_price * item.quantity for item in obj.items.all())
