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
        
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response["X-User-Id"] = str(payload.get("sub", ""))
        response["X-Role"] = str(payload.get("role", "customer"))
        return response
