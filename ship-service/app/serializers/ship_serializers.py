from rest_framework import serializers
from app.models import Shipping, ShippingAddress, ShippingStatus, ShippingMethod, ShippingFeature


class ShippingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingFeature
        fields = ["feature", "value"]


class ShippingMethodSerializer(serializers.ModelSerializer):
    features = ShippingFeatureSerializer(many=True, read_only=True)
    class Meta:
        model = ShippingMethod
        fields = "__all__"


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        exclude = ["shipping"]


class ShippingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingStatus
        fields = ["status", "description", "updated_date"]


class ShippingSerializer(serializers.ModelSerializer):
    address = ShippingAddressSerializer(read_only=True)
    statuses = ShippingStatusSerializer(many=True, read_only=True)
    method_name = serializers.CharField(source="shipping_method.method_name", read_only=True)

    class Meta:
        model = Shipping
        fields = "__all__"
