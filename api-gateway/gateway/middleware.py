"""
JWTAuthMiddleware
─────────────────
Validates JWT tokens and injects X-User-* headers into every request
forwarded to downstream microservices.

Token sources (in priority order):
  1. Authorization: Bearer <token>   (REST API clients)
  2. request.session["access_token"] (HTML browser clients)

Downstream services receive:
  X-User-Id     – user PK in the originating service's DB
  X-User-Role   – "customer" | "staff" | "manager"
  X-Entity-Id   – customer_id / staff_id
  X-Username    – username string
"""
import os
import logging

import jwt
from django.shortcuts import redirect
from django.conf import settings

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"

# Routes that never require a token
PUBLIC_PATHS = {
    "/",
    "/login/",
    "/register/",
    "/auth/refresh/",
}

# Path prefixes that are public (e.g. static files, products listing)
PUBLIC_PREFIXES = (
    "/static/",
    "/products",
    "/catalog",
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _decode(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(f"[DEBUG] Decoded JWT successfully: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        print("[DEBUG] JWT expired")
        logger.debug("JWT expired")
    except jwt.InvalidTokenError as e:
        print(f"[DEBUG] Invalid JWT: {e}")
        logger.debug(f"Invalid JWT: {e}")
    return None


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── 1. Extract token ─────────────────────────────────────────────────
        token = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            print(f"[DEBUG] Found token from header: {token[:10]}...")
        elif "access_token" in request.session:
            token = request.session["access_token"]
            print(f"[DEBUG] Found token from session: {token[:10]}...")
        else:
            print("[DEBUG] No token found in request")

        # ── 2. Decode & attach user context ──────────────────────────────────
        payload = _decode(token) if token else None
        request.jwt_payload = payload   # None if unauthenticated / expired
        print(f"[DEBUG] Request payload set to: {payload}")

        # ── 3. Guard protected routes (HTML only) ─────────────────────────────
        accepts_html = "text/html" in request.META.get("HTTP_ACCEPT", "")
        if not payload and not _is_public(request.path) and accepts_html:
            return redirect("login")

        return self.get_response(request)
