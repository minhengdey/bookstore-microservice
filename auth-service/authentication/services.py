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
        password = data.get("password", "")

        if AuthUser.objects.filter(username=username).exists():
            raise ValidationError("Username already taken")
        if AuthUser.objects.filter(email=email).exists():
            raise ValidationError("Email already registered")

        with transaction.atomic():
            user = AuthUser(
                username=username,
                email=email,
                is_staff=role in ("staff", "admin"),
                is_superuser=role == "admin",
            )
            user.set_password(password)
            user.save()

        try:
            profile = self._provision_profile(user, data, role, request_id=request_id)
        except AuthError as exc:
            user.delete()
            self._audit(
                "register",
                False,
                user,
                role,
                str(user.id),
                request_ip,
                user_agent,
                failure_reason=str(exc),
            )
            raise

        if not profile or not profile.get("auth_user_id"):
            self._compensate_profile(user, request_id)
            user.delete()
            raise ValidationError("Profile provisioning failed")

        claims = self._build_claims(user, profile)
        tokens = TokenService.issue_token_pair(claims)
        self._audit("register", True, user, role, str(user.id), request_ip, user_agent)

        payload = {
            "user": self._build_user_payload(user, profile),
            **tokens,
        }
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

        # locked check
        try:
            failed_count = getattr(user, "failed_login_count", 0)
            locked_until = getattr(user, "locked_until", None)
            if locked_until and locked_until > timezone.now():
                self._audit(
                    "login", False, user, role or "", str(user.id), request_ip, user_agent, failure_reason="account_locked"
                )
                raise AccountLocked("Account locked. Try again later")
        except AttributeError:
            pass

        try:
            profile = self._fetch_profile(user, request_id=request_id)
        except AuthError as exc:
            logger.warning("Profile fetch failed: %s", exc)
            profile = None

        if profile:
            status = profile.get("status", "ACTIVE")
            if status in ("SUSPENDED", "BANNED"):
                raise InvalidCredentials(f"Account is {status}")

        actual_roles = profile.get("roles", ["CUSTOMER"]) if profile else ["CUSTOMER"]
        actual_role_str = ",".join(actual_roles)

        if role and role.upper() not in [r.upper() for r in actual_roles]:
            self._register_failed_login(user, request_ip, user_agent, "invalid_role", actual_role_str)
            raise InvalidCredentials("Invalid credentials")
        if not user.check_password(password):
            self._register_failed_login(user, request_ip, user_agent, "invalid_credentials", actual_role_str)
            raise InvalidCredentials("Invalid credentials")

        user.last_login_at = timezone.now()
        if hasattr(user, "failed_login_count"):
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_count", "locked_until", "last_login_at"])
        else:
            user.save(update_fields=["last_login_at"])

        claims = self._build_claims(user, profile)
        tokens = TokenService.issue_token_pair(claims)
        self._audit("login", True, user, actual_role_str, str(user.id), request_ip, user_agent)

        payload = {
            "user": self._build_user_payload(user, profile),
            **tokens,
        }
        if include_profile and profile:
            payload["profile"] = profile
        return payload

    def refresh(self, refresh_token: str) -> dict:
        return TokenService.refresh_access(refresh_token)

    def _provision_profile(
        self, user: AuthUser, data: dict, role: str, request_id: str | None = None
    ) -> dict:
        payload = {
            "auth_user_id": str(user.id),
            "full_name": data.get("full_name", data.get("username", user.username)),
            "phone": data.get("phone", ""),
            "roles": [role.upper()],
        }
        try:
            return self.user_client.post("/internal/users/", payload, request_id=request_id)
        except UpstreamServiceError as exc:
            if exc.status_code in (400, 409):
                raise ValidationError("Profile creation failed", detail=exc.detail) from exc
            raise

    def _fetch_profile(self, user: AuthUser, request_id: str | None = None) -> dict | None:
        return self.user_client.get(
            f"/internal/users/{user.id}/", request_id=request_id
        )

    def _build_claims(self, user: AuthUser, profile: dict | None) -> dict:
        roles = profile.get("roles", ["CUSTOMER"]) if profile else ["CUSTOMER"]
        status = profile.get("status", "ACTIVE") if profile else "ACTIVE"
        role_version = profile.get("role_version", 1) if profile else 1
        
        claims = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "username": user.username,
            "roles": [r.upper() for r in roles],
            "status": status,
            "role_version": role_version,
            "entity_id": str(profile.get("entity_id")) if profile and profile.get("entity_id") else str(user.id),
        }
        if profile and profile.get("department"):
            claims["entity_role"] = profile.get("position", "")
        return claims

    def _build_user_payload(self, user: AuthUser, profile: dict | None) -> dict:
        roles = profile.get("roles", ["CUSTOMER"]) if profile else ["CUSTOMER"]
        status = profile.get("status", "ACTIVE") if profile else "ACTIVE"
        role_version = profile.get("role_version", 1) if profile else 1
        payload = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": [r.upper() for r in roles],
            "status": status,
            "role_version": role_version,
            "entity_id": str(profile.get("entity_id")) if profile and profile.get("entity_id") else str(user.id),
        }
        return payload

    def _audit(
        self,
        event_type: str,
        success: bool,
        user: AuthUser | None,
        role: str,
        entity_id: str | None,
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
        self, user: AuthUser, request_ip: str, user_agent: str, reason: str, role: str
    ) -> None:
        if hasattr(user, "failed_login_count"):
            user.failed_login_count += 1
            if user.failed_login_count >= settings.AUTH_MAX_FAILED_LOGINS:
                user.locked_until = timezone.now() + timedelta(minutes=settings.AUTH_LOCK_MINUTES)
            user.save(update_fields=["failed_login_count", "locked_until"])
            
        self._audit(
            "login",
            False,
            user,
            role,
            str(user.id),
            request_ip,
            user_agent,
            failure_reason=reason,
        )
