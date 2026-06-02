from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "api-gateway-dev-key")
DEBUG = True
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "api-gateway",
    "api-gateway:8000",
    "*.localhost",
    "*"  # Allow all for proxy validation via X-Forwarded-Host
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "gateway",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "gateway.middleware.JWTAuthMiddleware",
]

ROOT_URLCONF = "api_gateway.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
            ],
        },
    },
]

# Session storage (cache/memory-based — no disk path needed for the gateway)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_AGE = 86400 * 7   # 7 days
SESSION_COOKIE_HTTPONLY = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── JWT ────────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "bookstore-super-secret-jwt-2026")

# ── Service URLs ───────────────────────────────────────────────────────────────
SERVICE_URLS = {
    "auth":        os.environ.get("AUTH_SERVICE_URL",        "http://auth-service:8000"),
    "user":        os.environ.get("USER_SERVICE_URL",        "http://user-service:8000"),
    "product":     os.environ.get("PRODUCT_SERVICE_URL",     "http://product-service:8000"),
    "cart":        os.environ.get("CART_SERVICE_URL",        "http://cart-service:8000"),
    "order":       os.environ.get("ORDER_SERVICE_URL",       "http://order-service:8000"),
    "pay":         os.environ.get("PAY_SERVICE_URL",         "http://payment-service:8000"),
    "ship":        os.environ.get("SHIP_SERVICE_URL",        "http://shipping-service:8000"),
    "recommender": os.environ.get("RECOMMENDER_URL",         "http://recommender-ai-service:8000"),
}

# Proxy / secure settings (environment-driven; safe defaults for local/dev)
USE_X_FORWARDED_HOST = True  # Always trust X-Forwarded-Host from nginx
USE_X_FORWARDED_PORT = True  # Trust X-Forwarded-Port from nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Trust X-Forwarded-Proto from nginx
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"  # Lax to allow redirects from external sites
CSRF_TRUSTED_ORIGINS = (
    os.environ.get("CSRF_TRUSTED_ORIGINS", "").split() if os.environ.get("CSRF_TRUSTED_ORIGINS") else []
)

# ── Cache (Redis via django-redis) ──────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
    }
}

# Session backend uses cache (Redis) for shared sessions across workers
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
