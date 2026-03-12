from rest_framework import serializers
from app.models import User, Customer, WebAddress


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "phone", "is_active", "created_date"]
        read_only_fields = ["id", "created_date"]


class WebAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebAddress
        fields = "__all__"
        read_only_fields = ["id"]


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    addresses = WebAddressSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "user", "loyalty_points", "created_date", "addresses"]
        read_only_fields = ["id", "created_date"]


class CustomerRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=255, write_only=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
