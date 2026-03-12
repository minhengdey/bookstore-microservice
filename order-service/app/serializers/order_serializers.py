from rest_framework import serializers
from app.models import Order, OrderItem, OrderDiscount, Discount, Invoice


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    class Meta:
        model = OrderItem
        fields = ["id", "book_id", "quantity", "unit_price", "discount", "subtotal"]


class OrderDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDiscount
        fields = ["discount_id", "applied_value"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    order_discounts = OrderDiscountSerializer(many=True, read_only=True)
    invoice = InvoiceSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "customer_id", "order_date", "status",
            "shipping_fee", "discount_amount", "total_amount",
            "notes", "items", "order_discounts", "invoice",
        ]


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = "__all__"
