from uuid import uuid4
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.cache import cache

from .exceptions import AuthError
from .permissions import HasValidJWT
from .serializers import LoginSerializer, RefreshSerializer, RegisterSerializer
from .services import AuthService, TokenService
from .models import AuthAudit
from .logging_utils import set_request_id

_auth_service = AuthService()


def _get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def _rate_limit_login(ip_address: str) -> bool:
    if not ip_address:
        return False
    key = f"auth-login:{ip_address}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=settings.AUTH_LOGIN_RATE_WINDOW)
        count = 1
    return count > settings.AUTH_LOGIN_RATE_LIMIT


def _audit_rate_limited(ip_address: str, user_agent: str) -> None:
    try:
        AuthAudit.objects.create(
            event_type="login",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="rate_limited",
        )
    except Exception:
        return


def _error_response(exc: AuthError) -> Response:
    payload = {"error": exc.message}
    if exc.detail:
        payload["detail"] = exc.detail
    return Response(payload, status=exc.status_code)


def _request_id_from_headers(request) -> str:
    return request.META.get("HTTP_X_REQUEST_ID") or str(uuid4())


def _attach_request_id(response: Response, request_id: str) -> Response:
    response["X-Request-ID"] = request_id
    return response


class RegisterView(APIView):
    def post(self, request):
        request_id = _request_id_from_headers(request)
        set_request_id(request_id)
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return _attach_request_id(
                Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST), request_id
            )
        try:
            result = _auth_service.register(
                serializer.validated_data,
                request_ip=_get_client_ip(request),
                user_agent=_get_user_agent(request),
                request_id=request_id,
            )
            return _attach_request_id(Response(result, status=status.HTTP_201_CREATED), request_id)
        except AuthError as exc:
            return _attach_request_id(_error_response(exc), request_id)


class LoginView(APIView):
    def post(self, request):
        request_id = _request_id_from_headers(request)
        set_request_id(request_id)
        client_ip = _get_client_ip(request)
        user_agent = _get_user_agent(request)
        if _rate_limit_login(client_ip):
            _audit_rate_limited(client_ip, user_agent)
            return _attach_request_id(
                Response(
                    {"error": "Too many requests"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                ),
                request_id,
            )
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _attach_request_id(
                Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST), request_id
            )
        data = serializer.validated_data
        include_profile = str(request.query_params.get("include_profile", "false")).lower()
        include_profile = include_profile in ("1", "true", "yes")
        try:
            result = _auth_service.login(
                data["identifier"],
                data["password"],
                data.get("role"),
                request_ip=client_ip,
                user_agent=user_agent,
                include_profile=include_profile,
                request_id=request_id,
            )
            return _attach_request_id(Response(result), request_id)
        except AuthError as exc:
            return _attach_request_id(_error_response(exc), request_id)


class RefreshView(APIView):
    def post(self, request):
        request_id = _request_id_from_headers(request)
        set_request_id(request_id)
        serializer = RefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return _attach_request_id(
                Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST), request_id
            )
        try:
            result = _auth_service.refresh(serializer.validated_data["refresh"])
            return _attach_request_id(Response(result), request_id)
        except AuthError as exc:
            return _attach_request_id(_error_response(exc), request_id)


class MeView(APIView):
    permission_classes = [HasValidJWT]

    def get(self, request):
        request_id = _request_id_from_headers(request)
        set_request_id(request_id)
        token = TokenService.extract_token(request)
        payload = TokenService.decode_token(token)
        return _attach_request_id(Response(payload), request_id)


class LiveHealthView(APIView):
    def get(self, request):
        return Response({"status": "live"}, status=status.HTTP_200_OK)

class ReadyHealthView(APIView):
    def get(self, request):
        try:
            from django.db import connection
            connection.ensure_connection()
            db_status = "ok"
        except Exception:
            db_status = "error"
            
        if db_status == "ok":
            return Response({"status": "ready", "database": db_status}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "not_ready", "database": db_status}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

class IntrospectTokenView(APIView):
    permission_classes = [HasValidJWT]
    
    def get(self, request):
        token = TokenService.extract_token(request)
        payload = TokenService.decode_token(token)
        user_id = payload.get("sub", "")
        
        # Redis cache check
        import redis
        import json
        import os
        from .exceptions import UpstreamServiceError
        from rest_framework.exceptions import AuthenticationFailed
        
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        try:
            r = redis.StrictRedis.from_url(redis_url, decode_responses=True)
            cache_key = f"user_profile:v1:{user_id}"
            cached_data = r.get(cache_key)
            if cached_data:
                profile = json.loads(cached_data)
            else:
                # Cache miss -> HTTP fallback
                user = type('obj', (object,), {'id': user_id})
                profile = _auth_service._fetch_profile(user)
                if profile:
                    # Cache it with 5 mins TTL
                    r.setex(cache_key, 300, json.dumps(profile))
        except UpstreamServiceError:
            # Fail closed if user-service is down
            raise AuthenticationFailed("Unable to verify user status (Service Unavailable)")
        except Exception:
            # Redis failure or other, fallback to payload for resilience?
            # User specifically asked for Fail Closed on User Service Down + Redis Miss.
            # If we reach here, it might be a general exception, but let's try to fetch if we haven't
            try:
                if 'profile' not in locals() or not profile:
                    user = type('obj', (object,), {'id': user_id})
                    profile = _auth_service._fetch_profile(user)
            except Exception:
                raise AuthenticationFailed("Unable to verify user status")

        if not profile:
            raise AuthenticationFailed("User profile not found")

        current_status = profile.get("status", "ACTIVE")
        current_role_version = profile.get("role_version", 1)

        if current_status in ("SUSPENDED", "BANNED"):
            raise AuthenticationFailed(f"Account is {current_status}")

        if str(payload.get("role_version", 1)) != str(current_role_version):
            raise AuthenticationFailed("Token revoked due to role changes")
        
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response["X-User-Id"] = str(user_id)
        response["X-Username"] = str(payload.get("username", ""))
        roles = payload.get("roles", ["CUSTOMER"])
        response["X-Roles"] = ",".join(roles) if isinstance(roles, list) else str(roles)
        response["X-User-Status"] = str(current_status)
        response["X-Role-Version"] = str(current_role_version)
        return response
