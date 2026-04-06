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
    ('0 2 * * *', 'django.core.management.call_command', ['train_ai'])
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

# Implicit ALS (train: python manage.py train_implicit_cf --ratings ...)
IMPLICIT_CF_DATA_DIR = Path(
    os.environ.get("IMPLICIT_CF_DATA_DIR", str(BASE_DIR / "data" / "implicit_cf"))
)
# Độ mạnh điểm ALS khi trộn với co-buy + behavior (càng lớn càng ưu tiên ALS)
IMPLICIT_CF_ALS_WEIGHT = float(os.environ.get("IMPLICIT_CF_ALS_WEIGHT", "4.0"))
