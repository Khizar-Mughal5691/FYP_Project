"""Django settings for the Meta-Fut A.I API.

The API has no user accounts and no database yet: profiles and models come from the trained bundle
in METAFUT_DATA. Values for a real deployment come from environment variables; the defaults are for
running on a laptop during development.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("METAFUT_SECRET_KEY", "development-only-key-set-METAFUT_SECRET_KEY-to-deploy")
DEBUG = os.environ.get("METAFUT_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("METAFUT_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "metafut_api.urls"
WSGI_APPLICATION = "metafut_api.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

# No database is needed yet. Saved scenarios (later) will add PostgreSQL here.
DATABASES = {}

STATIC_URL = "static/"
USE_TZ = True
TIME_ZONE = "Asia/Karachi"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

# The React development server (Vite uses port 5173, Create React App 3000) may call the API.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "METAFUT_FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000").split(",")
