"""
Django settings for the Crumbly College Bakery project.

This project intentionally keeps the configuration simple and
beginner-friendly. Read the comments below — they explain *why*
each setting exists, not just what it does.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================================
# .env SUPPORT (no extra dependency required)
# ==========================================================
# A tiny, dependency-free loader: if a ".env" file exists next to
# manage.py, read simple KEY=VALUE lines from it into os.environ
# (without overwriting variables already set in the real
# environment). This lets you keep secrets (SECRET_KEY, DEBUG,
# ALLOWED_HOSTS, COLLEGE_EMAIL_DOMAIN, ...) out of source control by
# copying .env.example to .env and editing it — see README.md.
import os


def _load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default):
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


# ==========================================================
# SECURITY
# ==========================================================
# NOTE: The fallback value below is fine for local development / a
# college project, but MUST be overridden (via .env or a real
# environment variable) before deploying anywhere public.
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-crumbly-demo-secret-key-change-me")

# DEBUG = True is fine for local development. Set DEBUG=False (via
# .env) and configure ALLOWED_HOSTS before deploying anywhere real.
DEBUG = _env_bool("DEBUG", True)

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", ["*"])


# ==========================================================
# COLLEGE EMAIL DOMAIN
# ==========================================================
# Only students with an email ending in this domain may register.
# Change this via .env (or the environment variable directly) to
# match your own college's email domain — see also
# frontend/js/app.js's COLLEGE_EMAIL_DOMAIN constant, which must be
# kept in sync (it only drives the instant frontend hint; this is
# what's actually enforced).
COLLEGE_EMAIL_DOMAIN = os.environ.get("COLLEGE_EMAIL_DOMAIN", "@yourcollege.edu")


# ==========================================================
# APPLICATIONS
# ==========================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "bakery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # The existing frontend HTML files live here. They contain no
        # Django template tags, so they render as plain HTML — this
        # just lets Django serve them without a second web server.
        "DIRS": [BASE_DIR / "frontend"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"


# ==========================================================
# DATABASE — SQLite (as required for this project)
# ==========================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ==========================================================
# STATIC FILES (CSS, JavaScript)
# ==========================================================
# The existing frontend keeps its CSS/JS in frontend/css and
# frontend/js, and the HTML references them with plain relative
# paths like "css/style.css" and "js/app.js". To avoid having to
# rewrite every <link>/<script> tag, we serve those two folders
# directly at /css/ and /js/ (see backend/urls.py).
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "css", BASE_DIR / "frontend" / "js"]
STATIC_ROOT = BASE_DIR / "staticfiles"


# ==========================================================
# MEDIA FILES (uploaded cake reference images)
# ==========================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Reference images must not exceed 2 MB (also enforced in the
# CakeOrder serializer — this is just a sane server-wide default).
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# DJANGO REST FRAMEWORK
# ==========================================================
# Authentication approach (explained in full in README.md):
#
# The frontend is plain HTML + vanilla JavaScript, served BY this
# same Django application (see backend/urls.py). Because everything
# is same-origin, we use Django's built-in, battle-tested SESSION
# authentication rather than introducing token auth / JWT, which
# would add complexity this project doesn't need.
#
#   1. Student/bakery login calls Django's authenticate() + login(),
#      which sets a session cookie the browser stores automatically.
#   2. Every following request is authenticated via that cookie —
#      no manual token handling in JavaScript.
#   3. Django's CSRF protection is kept ON for all "unsafe" requests
#      (POST/PATCH/DELETE) made by an already-logged-in user. The
#      frontend's js/api.js reads the csrftoken cookie and sends it
#      back as the X-CSRFToken header, exactly as Django expects.
#   4. The three "login/register" endpoints are the only ones marked
#      @csrf_exempt, because a brand-new visitor has no session yet
#      to protect — see bakery/views.py for details.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "EXCEPTION_HANDLER": "bakery.views.friendly_exception_handler",
}

# The frontend and backend share the same origin, so the default
# Django CSRF cookie settings work out of the box — no CORS package
# needed (see README.md, section "Why no CORS?").
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True


# ==========================================================
# ADMIN BRANDING
# ==========================================================
# Cosmetic only — makes /admin/ say "Crumbly" instead of the Django
# default. Set in backend/urls.py via admin.site.site_header etc.
