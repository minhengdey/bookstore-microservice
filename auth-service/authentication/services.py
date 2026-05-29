import json
import os
import hmac
import hashlib
import logging
import time
from datetime import timedelta

import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from .exceptions import (
    AuthError,
    AccountLocked,
    CircuitBreakerOpen,
    InvalidCredentials,
    TokenValidationError,
    UpstreamServiceError,
    ValidationError,
)
from .models import AuthAudit, AuthUser
from .validators import normalize_role

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.opened_at = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.recovery_timeout:
            self.opened_at = None
            self.failure_count = 0
            return True
        return False

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.time()


class UpstreamClient:
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.breaker = CircuitBreaker(
            settings.AUTH_CIRCUIT_FAIL_THRESHOLD,
            settings.AUTH_CIRCUIT_RESET_SECONDS,
        )
        self.client = httpx.Client(timeout=settings.AUTH_SERVICE_TIMEOUT)

    def _headers(self) -> dict:
        return {
            "X-Internal-Token": settings.AUTH_INTERNAL_TOKEN,
            "X-Service-Name": "auth-service",
        }

    def _signature(self, timestamp: str, body: str) -> str:
        payload = f"{timestamp}.{body}".encode("utf-8")
        return hmac.new(
            settings.INTERNAL_SIGNING_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    def _signed_headers(self, body: str, request_id: str | None) -> dict:
        timestamp = str(int(time.time()))
        signature = self._signature(timestamp, body)
        headers = {
            **self._headers(),
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    def _safe_json(self, response: httpx.Response) -> dict:
        try:
            return response.json()
        except ValueError:
            return {}

    def _error_from_response(self, response: httpx.Response) -> UpstreamServiceError:
        detail = self._safe_json(response)
        message = detail.get("error") or detail.get("detail") or "Upstream error"
        retryable = response.status_code >= 500
        return UpstreamServiceError(
            f"{self.name} responded with {response.status_code}: {message}",
            status_code=response.status_code,
            detail=detail,
            retryable=retryable,
        )

    @retry(
        wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
        stop=stop_after_attempt(settings.AUTH_RETRY_ATTEMPTS),
        retry=retry_if_exception(lambda exc: isinstance(exc, UpstreamServiceError) and exc.retryable),
        reraise=True,
    )
    def post(self, path: str, payload: dict, request_id: str | None = None) -> dict:
        if not self.breaker.allow():
            raise CircuitBreakerOpen(f"{self.name} circuit breaker is open")
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        try:
            response = self.client.post(
                f"{self.base_url}{path}",
                content=body,
                headers=self._signed_headers(body, request_id),
            )
        except httpx.RequestError as exc:
            self.breaker.record_failure()
            raise UpstreamServiceError(
                f"{self.name} request failed", detail=str(exc), retryable=True
            ) from exc

        if response.status_code >= 400:
            error = self._error_from_response(response)
            if error.retryable:
                self.breaker.record_failure()
            else:
                self.breaker.record_success()
            raise error

        self.breaker.record_success()
        return self._safe_json(response)

    @retry(
        wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
        stop=stop_after_attempt(settings.AUTH_RETRY_ATTEMPTS),
        retry=retry_if_exception(lambda exc: isinstance(exc, UpstreamServiceError) and exc.retryable),
        reraise=True,
    )
    def get(self, path: str, params: dict | None = None, request_id: str | None = None) -> dict:
        if not self.breaker.allow():
            raise CircuitBreakerOpen(f"{self.name} circuit breaker is open")
        body = ""
        try:
            response = self.client.get(
                f"{self.base_url}{path}",
                params=params or {},
                headers=self._signed_headers(body, request_id),
            )
        except httpx.RequestError as exc:
            self.breaker.record_failure()
            raise UpstreamServiceError(
                f"{self.name} request failed", detail=str(exc), retryable=True
            ) from exc

        if response.status_code >= 400:
            error = self._error_from_response(response)
            if error.retryable:
                self.breaker.record_failure()
            else:
                self.breaker.record_success()
            raise error

        self.breaker.record_success()
        return self._safe_json(response)

    @retry(
        wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
        stop=stop_after_attempt(settings.AUTH_RETRY_ATTEMPTS),
        retry=retry_if_exception(lambda exc: isinstance(exc, UpstreamServiceError) and exc.retryable),
        reraise=True,
    )
    def delete(self, path: str, params: dict | None = None, request_id: str | None = None) -> dict:
        if not self.breaker.allow():
            raise CircuitBreakerOpen(f"{self.name} circuit breaker is open")
        body = ""
        try:
            response = self.client.delete(
                f"{self.base_url}{path}",
                params=params or {},
                headers=self._signed_headers(body, request_id),
            )
        except httpx.RequestError as exc:
            self.breaker.record_failure()
            raise UpstreamServiceError(
                f"{self.name} request failed", detail=str(exc), retryable=True
            ) from exc

        if response.status_code >= 400:
            error = self._error_from_response(response)
            if error.retryable:
                self.breaker.record_failure()
            else:
                self.breaker.record_success()
            raise error

        self.breaker.record_success()
        return self._safe_json(response)


class TokenService:
    _backend = TokenBackend(
        algorithm=api_settings.ALGORITHM,
        signing_key=api_settings.SIGNING_KEY,
        verifying_key=api_settings.VERIFYING_KEY,
        audience=api_settings.AUDIENCE,
        issuer=api_settings.ISSUER,
        jwk_url=api_settings.JWK_URL,
        leeway=api_settings.LEEWAY,
    )

    @staticmethod
    def issue_token_pair(claims: dict) -> dict:
        refresh = RefreshToken()
        for key, value in claims.items():
            refresh[key] = value
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def refresh_access(refresh_token: str) -> dict:
        try:
            refresh = RefreshToken(refresh_token)
        except TokenError as exc:
            raise TokenValidationError("Invalid or expired token") from exc
        return {"access": str(refresh.access_token)}

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            UntypedToken(token)
        except TokenError as exc:
            raise TokenValidationError("Invalid or expired token") from exc
        return TokenService._backend.decode(token, verify=True)

    @staticmethod
    def extract_token(request) -> str:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Bearer "):
            return header[7:]
        return ""


class AuthService:
    def __init__(self):
        self.user_client = UpstreamClient(
            os.environ.get("USER_SERVICE_URL", "http://user-service:8000"), "user-service"
        )

    def register(
        self,
        data: dict,
        request_ip: str = "",
        user_agent: str = "",
        request_id: str | None = None,
    ) -> dict:
        role = normalize_role(data.get("role") or "customer")
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "")
        password = data.get("password", "")

        if AuthUser.objects.filter(username=username).exists():
            raise ValidationError("Username already taken")
        if AuthUser.objects.filter(email=email).exists():
            raise ValidationError("Email already registered")

        with transaction.atomic():
            user = AuthUser(
                username=username,
                email=email,
                phone=phone,
                role=role,
                entity_role="manager" if role == "admin" else ("staff" if role == "staff" else ""),
            )
            user.set_password(password)
            user.save()

        try:
            profile = self._provision_profile(user, data, request_id=request_id)
        except AuthError as exc:
            user.delete()
            self._audit(
                "register",
                False,
                user,
                user.role,
                user.entity_id,
                request_ip,
                user_agent,
                failure_reason=str(exc),
            )
            raise

        entity_id = profile.get("id") if isinstance(profile, dict) else None
        if not entity_id:
            self._compensate_profile(user, request_id)
            user.delete()
            raise ValidationError("Profile provisioning failed")

        try:
            user.entity_id = entity_id
            user.save(update_fields=["entity_id"])
        except Exception as exc:
            self._compensate_profile(user, request_id)
            user.delete()
            raise ValidationError("User update failed") from exc

        claims = self._build_claims(user)
        tokens = TokenService.issue_token_pair(claims)
        self._audit(
            "register",
            True,
            user,
            user.role,
            user.entity_id,
            request_ip,
            user_agent,
        )

        payload = {
            "user": self._build_user_payload(user),
            **tokens,
        }
        if user.role == "customer":
            payload["customer"] = profile
        else:
            payload["staff"] = profile
        return payload

    def login(
        self,
        identifier: str,
        password: str,
        role: str | None,
        request_ip: str = "",
        user_agent: str = "",
        include_profile: bool = False,
        request_id: str | None = None,
    ) -> dict:
        role = normalize_role(role) if role else None
        identifier = identifier.strip()
        user = (
            AuthUser.objects.filter(username=identifier).first()
            or AuthUser.objects.filter(email=identifier.lower()).first()
        )
        if not user or not user.is_active:
            self._audit(
                "login",
                False,
                user,
                role or "",
                None,
                request_ip,
                user_agent,
                failure_reason="invalid_credentials",
            )
            raise InvalidCredentials("Invalid credentials")

        if user.locked_until and user.locked_until > timezone.now():
            self._audit(
                "login",
                False,
                user,
                user.role,
                user.entity_id,
                request_ip,
                user_agent,
                failure_reason="account_locked",
            )
            raise AccountLocked("Account locked. Try again later")
        if role and user.role != role:
            self._register_failed_login(user, request_ip, user_agent, "invalid_role")
            raise InvalidCredentials("Invalid credentials")
        if not user.check_password(password):
            self._register_failed_login(user, request_ip, user_agent, "invalid_credentials")
            raise InvalidCredentials("Invalid credentials")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = timezone.now()
        user.save(update_fields=["failed_login_count", "locked_until", "last_login_at"])

        claims = self._build_claims(user)
        tokens = TokenService.issue_token_pair(claims)
        self._audit(
            "login",
            True,
            user,
            user.role,
            user.entity_id,
            request_ip,
            user_agent,
        )

        payload = {
            "user": self._build_user_payload(user),
            **tokens,
        }
        if include_profile:
            try:
                profile = self._fetch_profile(user, request_id=request_id)
            except AuthError as exc:
                logger.warning("Profile fetch failed: %s", exc)
                profile = None
            if user.role == "customer":
                payload["customer"] = profile
            else:
                payload["staff"] = profile
        return payload

    def refresh(self, refresh_token: str) -> dict:
        return TokenService.refresh_access(refresh_token)

    def _provision_profile(
        self, user: AuthUser, data: dict, request_id: str | None = None
    ) -> dict:
        if user.role == "customer":
            payload = {
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "external_id": user.id,
            }
            return self._create_customer_profile(payload, request_id=request_id)

        staff_role = user.entity_role or "staff"
        payload = {
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "external_id": user.id,
            "storage_code": data.get("storage_code"),
            "department": data.get("department", ""),
            "position": data.get("position", ""),
            "role": staff_role,
        }
        return self._create_staff_profile(payload, request_id=request_id)

    def _fetch_profile(self, user: AuthUser, request_id: str | None = None) -> dict | None:
        # User-service directly maps user.id
        return self.user_client.get(
            f"/internal/users/{user.id}/", request_id=request_id
        )

    def _create_customer_profile(self, payload: dict, request_id: str | None = None) -> dict:
        try:
            # We pass 'id' from AuthUser external_id which we mapped to payload['external_id']
            payload["id"] = payload.pop("external_id")
            payload["role"] = "customer"
            return self.user_client.post(
                "/internal/users/", payload, request_id=request_id
            )
        except UpstreamServiceError as exc:
            if exc.status_code in (400, 409):
                raise ValidationError("Customer profile creation failed", detail=exc.detail) from exc
            raise

    def _create_staff_profile(self, payload: dict, request_id: str | None = None) -> dict:
        try:
            payload["id"] = payload.pop("external_id")
            return self.user_client.post(
                "/internal/users/", payload, request_id=request_id
            )
        except UpstreamServiceError as exc:
            if exc.status_code in (400, 409):
                raise ValidationError("Staff profile creation failed", detail=exc.detail) from exc
            raise

    def _build_claims(self, user: AuthUser) -> dict:
        claims = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "entity_id": user.entity_id,
        }
        if user.entity_role:
            claims["entity_role"] = user.entity_role
        return claims

    def _build_user_payload(self, user: AuthUser) -> dict:
        payload = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "entity_id": user.entity_id,
        }
        if user.entity_role:
            payload["entity_role"] = user.entity_role
        return payload

    def _audit(
        self,
        event_type: str,
        success: bool,
        user: AuthUser,
        role: str,
        entity_id: int | None,
        ip_address: str,
        user_agent: str,
        failure_reason: str = "",
    ) -> None:
        try:
            AuthAudit.objects.create(
                event_type=event_type,
                success=success,
                user_id=user.id if user else None,
                role=role,
                entity_id=entity_id,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=failure_reason,
            )
        except Exception as exc:
            logger.warning("Failed to write auth audit: %s", exc)

    def _compensate_profile(self, user: AuthUser, request_id: str | None = None) -> None:
        try:
            self.user_client.delete(
                f"/internal/users/{user.id}/", request_id=request_id
            )
        except AuthError as exc:
            logger.warning("Compensation failed: %s", exc)

    def _register_failed_login(
        self, user: AuthUser, request_ip: str, user_agent: str, reason: str
    ) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= settings.AUTH_MAX_FAILED_LOGINS:
            user.locked_until = timezone.now() + timedelta(minutes=settings.AUTH_LOCK_MINUTES)
        user.save(update_fields=["failed_login_count", "locked_until"])
        self._audit(
            "login",
            False,
            user,
            user.role,
            user.entity_id,
            request_ip,
            user_agent,
            failure_reason=reason,
        )
