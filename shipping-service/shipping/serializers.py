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
    class Meta:
        model = ShippingStatus
        fields = "__all__"

class ShippingSerializer(serializers.ModelSerializer):
    address = ShippingAddressSerializer(read_only=True)
    statuses = ShippingStatusSerializer(many=True, read_only=True)
    
    class Meta:
        model = Shipping
        fields = "__all__"
