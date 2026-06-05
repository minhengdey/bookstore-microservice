from rest_framework import serializers
from .validators import normalize_role, validate_password_strength

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField()
    role = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        identifier = (attrs.get("username") or attrs.get("email") or "").strip()
        if not identifier:
            raise serializers.ValidationError("username or email is required")
        attrs["identifier"] = identifier

        role = attrs.get("role")
        if role:
            try:
                attrs["role"] = normalize_role(role)
            except ValueError as exc:
                raise serializers.ValidationError({"role": str(exc)}) from exc
        return attrs

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)
    storage_code = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        role = attrs.get("role") or "CUSTOMER"
        try:
            attrs["role"] = normalize_role(role)
        except ValueError as exc:
            raise serializers.ValidationError({"role": str(exc)}) from exc

        if attrs["role"] not in ("CUSTOMER", "SELLER"):
            raise serializers.ValidationError({"role": "public registration only creates CUSTOMER or SELLER accounts"})

        return attrs

    def validate_password(self, value):
        try:
            validate_password_strength(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
