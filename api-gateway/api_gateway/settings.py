from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "api-gateway-dev-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

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
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "bookstore-jwt-secret-dev")

# ── Service URLs ───────────────────────────────────────────────────────────────
SERVICE_URLS = {
    "customer":    os.environ.get("CUSTOMER_SERVICE_URL",    "http://customer-service:8000"),
    "book":        os.environ.get("BOOK_SERVICE_URL",        "http://book-service:8000"),
    "catalog":     os.environ.get("CATALOG_SERVICE_URL",     "http://catalog-service:8000"),
    "cart":        os.environ.get("CART_SERVICE_URL",        "http://cart-service:8000"),
    "order":       os.environ.get("ORDER_SERVICE_URL",       "http://order-service:8000"),
    "pay":         os.environ.get("PAY_SERVICE_URL",         "http://pay-service:8000"),
    "ship":        os.environ.get("SHIP_SERVICE_URL",        "http://ship-service:8000"),
    "comment":     os.environ.get("COMMENT_RATE_URL",        "http://comment-rate-service:8000"),
    "recommender": os.environ.get("RECOMMENDER_URL",         "http://recommender-ai-service:8000"),
    "staff":       os.environ.get("STAFF_SERVICE_URL",       "http://staff-service:8000"),
    "manager":     os.environ.get("MANAGER_SERVICE_URL",     "http://manager-service:8000"),
}
