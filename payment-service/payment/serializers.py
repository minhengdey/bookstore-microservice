from rest_framework import serializers

class CreatePaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    correlation_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(max_length=255, required=False)

class RefundPaymentSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
    idempotency_key = serializers.CharField(max_length=255, required=False)
