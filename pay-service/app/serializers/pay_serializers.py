from rest_framework import serializers
from app.models import Payment, PaymentMethod, Refund, Transaction


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(source="payment_method.method_name", read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
