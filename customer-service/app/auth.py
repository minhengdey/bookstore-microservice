"""JWT helpers for customer-service."""
import os
import jwt
from datetime import datetime, timezone, timedelta

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "bookstore-jwt-secret-dev")
JWT_ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 60 * 24   # 24 h
REFRESH_EXPIRE_DAYS = 7


def create_access_token(payload: dict) -> str:
    data = {**payload}
    data["exp"] = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_EXPIRE_MINUTES)
    data["token_type"] = "access"
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(payload: dict) -> str:
    data = {**payload}
    data["exp"] = datetime.now(tz=timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    data["token_type"] = "refresh"
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def build_token_pair(user, entity_id: int) -> dict:
    payload = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": "customer",
        "entity_id": entity_id,
    }
    return {
        "access": create_access_token(payload),
        "refresh": create_refresh_token(payload),
    }
