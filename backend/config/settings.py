import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = ["corsheaders", "routing"]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Stateless JSON API: no database, sessions, or cookies, hence no CSRF middleware.
DATABASES = {}
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Comma-separated list of frontend origins, e.g. "https://my-app.vercel.app".
_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [o for o in _origins.split(",") if o]
CORS_ALLOW_ALL_ORIGINS = not CORS_ALLOWED_ORIGINS and DEBUG

# Simulated-storm demo mode (see routing/demo.py). On in development, off in
# production unless explicitly enabled with DEMO_WEATHER_ENABLED=1.
DEMO_WEATHER_ENABLED = os.environ.get("DEMO_WEATHER_ENABLED", "1" if DEBUG else "0") == "1"
