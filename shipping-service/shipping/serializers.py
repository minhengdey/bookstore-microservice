from rest_framework import serializers
from .models import Shipping, ShippingMethod, ShippingFeature, ShippingAddress, ShippingStatus

class ShippingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingFeature
        fields = "__all__"

class ShippingMethodSerializer(serializers.ModelSerializer):
    features = ShippingFeatureSerializer(many=True, read_only=True)
    class Meta:
        model = ShippingMethod
        fields = "__all__"

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = "__all__"

class ShippingStatusSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source="updated_date", read_only=True)

    class Meta:
        model = ShippingStatus
        fields = "__all__"


class ShippingSerializer(serializers.ModelSerializer):
    address = ShippingAddressSerializer(read_only=True)
    statuses = ShippingStatusSerializer(many=True, read_only=True)
    tracking_number = serializers.SerializerMethodField()

    def get_tracking_number(self, obj):
        return f"SHIP-{obj.order_id:06d}"

    class Meta:
        model = Shipping
        fields = [
            "id", "order_id", "shipping_method", "status",
            "estimated_delivery_date", "created_date",
            "address", "statuses", "tracking_number",
        ]
