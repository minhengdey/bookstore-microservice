from rest_framework.permissions import BasePermission
from .services import TokenService
from .exceptions import TokenValidationError


class HasValidJWT(BasePermission):
    message = "Unauthorized"

    def has_permission(self, request, view):
        token = TokenService.extract_token(request)
        if not token:
            return False
        try:
            payload = TokenService.decode_token(token)
        except TokenValidationError:
            return False
        request.jwt_payload = payload
        return True
