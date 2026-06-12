from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """
    Minimal .env loader cho môi trường local (không phụ thuộc python-dotenv).
    Không override biến đã có sẵn trong environment.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


# Ưu tiên file .env ở root monorepo, fallback .env trong service.
_load_env_file(BASE_DIR.parent / ".env")
_load_env_file(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "recommender-dev-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_crontab",
    "app",
]

CRONJOBS = [
    ('0 2 * * *', 'django.core.management.call_command', ['ensure_recommender_models', '--force']),
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = "recommender_service.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "recommender_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Behavior prediction model artifacts
RECOMMENDER_MODEL_PATH = Path(
    os.environ.get("RECOMMENDER_MODEL_PATH", str(BASE_DIR / "models" / "model_best.keras"))
)
RECOMMENDER_ENCODER_PATH = Path(
    os.environ.get("RECOMMENDER_ENCODER_PATH", str(BASE_DIR / "models" / "encoders.pkl"))
)
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")

# Implicit ALS (train: python manage.py train_implicit_cf --ratings ...)
IMPLICIT_CF_DATA_DIR = Path(
    os.environ.get("IMPLICIT_CF_DATA_DIR", str(BASE_DIR / "data" / "implicit_cf"))
)
# Độ mạnh điểm ALS khi trộn với co-buy + behavior (càng lớn càng ưu tiên ALS)
IMPLICIT_CF_ALS_WEIGHT = float(os.environ.get("IMPLICIT_CF_ALS_WEIGHT", "4.0"))
COOCCURRENCE_WEIGHT = float(os.environ.get("COOCCURRENCE_WEIGHT", "3.0"))
COPURCHASE_WEIGHT = float(os.environ.get("COPURCHASE_WEIGHT", "2.5"))
CATEGORY_AFFINITY_WEIGHT = float(os.environ.get("CATEGORY_AFFINITY_WEIGHT", "2.0"))

# Proxy / secure settings (environment-driven; safe defaults for local/dev)
USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "True").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"
CSRF_TRUSTED_ORIGINS = (
    os.environ.get("CSRF_TRUSTED_ORIGINS", "").split() if os.environ.get("CSRF_TRUSTED_ORIGINS") else []
)
