from rest_framework import serializers
from app.models import User, InventoryStaff


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]


class InventoryStaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = InventoryStaff
        fields = "__all__"


class StaffCreateSerializer(serializers.Serializer):
    username     = serializers.CharField(max_length=150)
    email        = serializers.EmailField()
    password     = serializers.CharField(write_only=True)
    phone        = serializers.CharField(required=False, allow_blank=True)
    storage_code = serializers.CharField(max_length=50)
    department   = serializers.CharField(required=False, allow_blank=True)
    position     = serializers.CharField(required=False, allow_blank=True)
    role         = serializers.ChoiceField(
        choices=["staff", "manager"], default="staff", required=False
    )
