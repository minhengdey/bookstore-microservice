from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password

from app.repositories import StaffRepository
from app.serializers import InventoryStaffSerializer
from app.auth import build_token_pair, decode_token, create_access_token

_repo = StaffRepository()


class StaffLoginView(APIView):
    """POST /auth/login/  →  {access, refresh, user}

    Works for both 'staff' and 'manager' roles (determined by inventory_staff.role).
    """

    def post(self, request):
        identifier = request.data.get("username", "").strip()
        password   = request.data.get("password", "")

        if not identifier or not password:
            return Response(
                {"error": "username/email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _repo.get_user_by_username(identifier) or _repo.get_user_by_email(identifier)

        if not user or not check_password(password, user.password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)

        staff = _repo.get_staff_by_user_id(user.id)
        if not staff:
            return Response({"error": "Staff profile not found"}, status=status.HTTP_404_NOT_FOUND)

        tokens = build_token_pair(user, staff)
        return Response({
            "user": {
                "id":         user.id,
                "username":  user.username,
                "email":     user.email,
                "role":       staff.role,
                "entity_id":  staff.id,
            },
            "staff": InventoryStaffSerializer(staff).data,
            **tokens,
        })


class StaffTokenRefreshView(APIView):
    """POST /auth/refresh/  →  {access}"""

    def post(self, request):
        refresh_token = request.data.get("refresh", "")
        if not refresh_token:
            return Response({"error": "refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = decode_token(refresh_token)
            if payload.get("token_type") != "refresh":
                raise ValueError("Not a refresh token")
            payload.pop("exp", None)
            payload.pop("token_type", None)
            return Response({"access": create_access_token(payload)})
        except Exception:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)


class StaffMeView(APIView):
    """GET /auth/me/  →  staff profile"""

    def get(self, request):
        user_id   = request.META.get("HTTP_X_USER_ID")
        entity_id = request.META.get("HTTP_X_ENTITY_ID")
        role      = request.META.get("HTTP_X_USER_ROLE")

        if not user_id or role not in ("staff", "manager"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        staff = _repo.get_by_id(int(entity_id))
        if not staff:
            return Response({"error": "Staff not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(InventoryStaffSerializer(staff).data)
