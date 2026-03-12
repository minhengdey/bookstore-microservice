"""Role-based permission decorators.

API Gateway injects X-User-* headers into every forwarded request.
These decorators read those headers and enforce access control.
"""
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def _ctx(request):
    return {
        "user_id":   request.META.get("HTTP_X_USER_ID"),
        "username":  request.META.get("HTTP_X_USERNAME"),
        "role":      request.META.get("HTTP_X_USER_ROLE"),
        "entity_id": request.META.get("HTTP_X_ENTITY_ID"),
    }


def require_auth(fn):
    """Any authenticated user."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        ctx = _ctx(request)
        if not ctx["user_id"]:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        request.user_ctx = ctx
        return fn(self, request, *args, **kwargs)
    return wrapper


def require_customer(fn):
    """Customer role only."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        ctx = _ctx(request)
        if not ctx["user_id"]:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if ctx["role"] != "customer":
            return Response({"error": "Customer access required"}, status=status.HTTP_403_FORBIDDEN)
        request.user_ctx = ctx
        return fn(self, request, *args, **kwargs)
    return wrapper


def require_staff(fn):
    """Staff or manager role."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        ctx = _ctx(request)
        if not ctx["user_id"]:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if ctx["role"] not in ("staff", "manager"):
            return Response({"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN)
        request.user_ctx = ctx
        return fn(self, request, *args, **kwargs)
    return wrapper


def require_manager(fn):
    """Manager role only."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        ctx = _ctx(request)
        if not ctx["user_id"]:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if ctx["role"] != "manager":
            return Response({"error": "Manager access required"}, status=status.HTTP_403_FORBIDDEN)
        request.user_ctx = ctx
        return fn(self, request, *args, **kwargs)
    return wrapper
