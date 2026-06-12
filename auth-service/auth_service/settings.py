from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "auth-service-dev-key")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "authentication",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "auth_service.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "auth_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "auth-db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SIMPLE_JWT = {
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.environ.get("JWT_SECRET_KEY", "ecommerce-super-secret-jwt-2026"),
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "1440"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "auth-service-cache",
    }
}

AUTH_USER_SERVICE_URL = os.environ.get(
    "USER_SERVICE_URL", "http://user-service:8000"
)
AUTH_USER_PROFILE_PATH = os.environ.get(
    "AUTH_USER_PROFILE_PATH", "/internal/users/"
)
AUTH_SERVICE_TIMEOUT = float(os.environ.get("AUTH_SERVICE_TIMEOUT", "2"))
AUTH_RETRY_ATTEMPTS = int(os.environ.get("AUTH_RETRY_ATTEMPTS", "2"))
AUTH_CIRCUIT_FAIL_THRESHOLD = int(os.environ.get("AUTH_CIRCUIT_FAIL_THRESHOLD", "5"))
AUTH_CIRCUIT_RESET_SECONDS = int(os.environ.get("AUTH_CIRCUIT_RESET_SECONDS", "30"))
AUTH_LOGIN_RATE_LIMIT = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT", "5"))
AUTH_LOGIN_RATE_WINDOW = int(os.environ.get("AUTH_LOGIN_RATE_WINDOW", "60"))
AUTH_MAX_FAILED_LOGINS = int(os.environ.get("AUTH_MAX_FAILED_LOGINS", "5"))
AUTH_LOCK_MINUTES = int(os.environ.get("AUTH_LOCK_MINUTES", "15"))
AUTH_INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "internal-dev-token")
INTERNAL_SIGNING_SECRET = os.environ.get("INTERNAL_SIGNING_SECRET", "internal-signing-secret")
INTERNAL_ALLOWED_SERVICES = os.environ.get("INTERNAL_ALLOWED_SERVICES", "auth-service")
INTERNAL_SIGNATURE_TOLERANCE = int(os.environ.get("INTERNAL_SIGNATURE_TOLERANCE", "30"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "{\"timestamp\":\"%(asctime)s\",\"level\":\"%(levelname)s\",\"service\":\"%(service)s\",\"request_id\":\"%(request_id)s\",\"logger\":\"%(name)s\",\"message\":\"%(message)s\"}"
        }
    },
    "filters": {
        "request_id": {
            "()": "authentication.logging_utils.RequestIdFilter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Proxy / secure settings (environment-driven; safe defaults for local/dev)
USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "True").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"
CSRF_TRUSTED_ORIGINS = (
    os.environ.get("CSRF_TRUSTED_ORIGINS", "").split() if os.environ.get("CSRF_TRUSTED_ORIGINS") else []
)

AUTH_USER_MODEL = "authentication.AuthUser"
