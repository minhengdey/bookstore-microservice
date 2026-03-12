from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password

from app.repositories import UserRepository, CustomerRepository
from app.serializers import CustomerSerializer, CustomerRegisterSerializer
from app.auth import build_token_pair, decode_token, create_access_token
from app.services import CustomerService

_user_repo = UserRepository()
_customer_repo = CustomerRepository()
_svc = CustomerService()


class CustomerLoginView(APIView):
    """POST /auth/login/  →  {access, refresh, user}"""

    def post(self, request):
        identifier = request.data.get("username", "").strip()
        password   = request.data.get("password", "")

        if not identifier or not password:
            return Response(
                {"error": "username/email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _user_repo.get_by_username(identifier) or _user_repo.get_by_email(identifier)

        if not user or not check_password(password, user.password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)

        customer = _customer_repo.get_by_user_id(user.id)
        if not customer:
            return Response({"error": "Customer profile not found"}, status=status.HTTP_404_NOT_FOUND)

        tokens = build_token_pair(user, customer.id)
        return Response({
            "user": {
                "id":         user.id,
                "username":   user.username,
                "email":      user.email,
                "role":       "customer",
                "entity_id":  customer.id,
            },
            **tokens,
        })


class CustomerTokenRefreshView(APIView):
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


class CustomerRegisterView(APIView):
    """POST /auth/register/  →  {customer, access, refresh}"""

    def post(self, request):
        ser = CustomerRegisterSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            customer = _svc.register_customer(user_data=dict(ser.validated_data))
            tokens = build_token_pair(customer.user, customer.id)
            return Response(
                {
                    "customer": CustomerSerializer(customer).data,
                    "user": {
                        "id":         customer.user.id,
                        "username":   customer.user.username,
                        "email":      customer.user.email,
                        "role":       "customer",
                        "entity_id":  customer.id,
                    },
                    **tokens,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomerMeView(APIView):
    """GET /auth/me/  →  customer profile (requires gateway auth headers)"""

    def get(self, request):
        user_id   = request.META.get("HTTP_X_USER_ID")
        entity_id = request.META.get("HTTP_X_ENTITY_ID")
        role      = request.META.get("HTTP_X_USER_ROLE")

        if not user_id or role != "customer":
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            customer = _svc.get_customer(int(entity_id))
            return Response(CustomerSerializer(customer).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
