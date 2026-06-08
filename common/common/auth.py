import os
import jwt
import hmac
import hashlib
import time
import functools
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "ecommerce-super-secret-jwt-2026")
JWT_ALGORITHM = "HS256"

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "internal-dev-token")
INTERNAL_SIGNING_SECRET = os.environ.get("INTERNAL_SIGNING_SECRET", "internal-signing-secret")
INTERNAL_ALLOWED_SERVICES = [
    item.strip() for item in os.environ.get("INTERNAL_ALLOWED_SERVICES", "auth-service").split(",")
]
INTERNAL_SIGNATURE_TOLERANCE = int(os.environ.get("INTERNAL_SIGNATURE_TOLERANCE", "30"))

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        raise ValueError(str(e))

def _get_context_from_headers(request):
    user_id = request.META.get("HTTP_X_USER_ID")
    role = request.META.get("HTTP_X_USER_ROLE") or request.META.get("HTTP_X_ROLE")
    entity_id = request.META.get("HTTP_X_ENTITY_ID") or user_id
    
    # Fallback to direct decoding if headers are missing (for local dev)
    if not user_id:
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_jwt(token)
                user_id = str(payload.get("user_id") or payload.get("sub") or "")
                entity_id = str(payload.get("entity_id") or user_id)
                role = payload.get("role", "customer")
        except Exception:
            pass
            
    return user_id, role, entity_id


def _attach_context(request, user_id, role, entity_id):
    request.user_id = int(user_id) if str(user_id).isdigit() else user_id
    request.user_ctx = {
        "user_id": user_id,
        "entity_id": entity_id or user_id,
        "role": role,
    }

def require_auth(view_func):
    @functools.wraps(view_func)
    def wrapper(view_instance, request, *args, **kwargs):
        user_id, role, entity_id = _get_context_from_headers(request)
        if not user_id:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        _attach_context(request, user_id, role, entity_id)
        return view_func(view_instance, request, *args, **kwargs)
    return wrapper

def _require_role(allowed_roles: list):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(view_instance, request, *args, **kwargs):
            user_id, role, entity_id = _get_context_from_headers(request)
            if not user_id:
                return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
            if role not in allowed_roles:
                return Response({"error": "Forbidden: Requires specific role"}, status=status.HTTP_403_FORBIDDEN)
            _attach_context(request, user_id, role, entity_id)
            return view_func(view_instance, request, *args, **kwargs)
        return wrapper
    return decorator

def require_customer(view_func): return _require_role(["customer"])(view_func)
def require_staff(view_func): return _require_role(["staff", "manager", "admin"])(view_func)
def require_manager(view_func): return _require_role(["manager", "admin"])(view_func)

def require_internal(fn):
    @functools.wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        token = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        service_name = request.META.get("HTTP_X_SERVICE_NAME", "")
        signature = request.META.get("HTTP_X_SIGNATURE", "")
        timestamp = request.META.get("HTTP_X_TIMESTAMP", "")
        
        if not token or token != INTERNAL_TOKEN:
            return Response({"error": "Forbidden - Invalid Token"}, status=status.HTTP_403_FORBIDDEN)
        if service_name not in INTERNAL_ALLOWED_SERVICES:
            return Response({"error": f"Forbidden - Service {service_name} not allowed"}, status=status.HTTP_403_FORBIDDEN)
        if not signature or not timestamp:
            return Response({"error": "Forbidden - Missing signature"}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            ts_int = int(timestamp)
        except ValueError:
            return Response({"error": "Forbidden - Invalid timestamp"}, status=status.HTTP_403_FORBIDDEN)
            
        if abs(int(time.time()) - ts_int) > INTERNAL_SIGNATURE_TOLERANCE:
            return Response({"error": "Forbidden - Request expired"}, status=status.HTTP_403_FORBIDDEN)
            
        body = request.body.decode("utf-8") if request.body else ""
        expected = hmac.new(
            INTERNAL_SIGNING_SECRET.encode("utf-8"),
            f"{timestamp}.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return Response({"error": "Forbidden - Invalid signature"}, status=status.HTTP_403_FORBIDDEN)
            
        return fn(self, request, *args, **kwargs)
    return wrapper
