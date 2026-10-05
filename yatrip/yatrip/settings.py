"""
Django settings for the Yatrip backend.

Configuration rules for this project:
  * No credential, secret or machine-specific path is ever hardcoded here.
  * Everything sensitive is read from environment variables (see .env).
  * Missing required configuration raises immediately at import time rather
    than silently falling back to an insecure default.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR points at the directory that contains manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the repo root first, then the backend's own copy as fallback.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "yatrip" / ".env")


def _env_flag(name, default=False):
    return (os.getenv(name) or str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_list(name, default=""):
    """Parse a comma-separated env var into a list of non-empty strings."""
    raw = os.getenv(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

# Never ship a fallback secret. Fail loudly so a missing SECRET_KEY cannot
# silently degrade into a known default.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Add it to your .env file. Generate one with:\n"
        '  python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )

DEBUG = _env_flag("DEBUG", False)

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_ENGINE = os.getenv("DB_ENGINE", "django.contrib.gis.db.backends.postgis")

_REQUIRED_DB_VARS = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
_missing_db_vars = [key for key in _REQUIRED_DB_VARS if not os.getenv(key)]
if _missing_db_vars:
    raise RuntimeError(
        "Missing database settings in .env: " + ", ".join(_missing_db_vars)
    )

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}


# ---------------------------------------------------------------------------
# Third-party service credentials
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "yatrip-rag")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# gemini-2.0-flash and the whole 2.x line are retired for this project (404).
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.8-flash")
# models/text-embedding-004 and models/embedding-001 are both retired (404).
# gemini-embedding-001 is the current model and emits 3072-dim vectors, so the
# Pinecone index has to be created with that same dimension.
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"
)
PINECONE_EMBEDDING_DIMENSION = int(os.getenv("PINECONE_EMBEDDING_DIMENSION", "3072"))

# Chat providers in preference order, as "provider:model" pairs. The chatbot
# walks this list whenever a provider is out of quota, so a single exhausted
# free tier does not take the assistant offline. Entries whose API key is not
# set are skipped automatically, so it is safe to list a provider before adding
# its key. See chatbot/llm.py.
LLM_PROVIDER_CHAIN = os.getenv(
    "LLM_PROVIDER_CHAIN",
    f"gemini:{GEMINI_CHAT_MODEL},groq:openai/gpt-oss-120b",
)

# The chatbot talks to an MCP server instead of scraping sources in-process.
MCP_SERVER_ENABLED = _env_flag("MCP_SERVER_ENABLED", True)
MCP_SERVER_TRANSPORT = os.getenv("MCP_SERVER_TRANSPORT", "stdio")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
# Absolute path to the MCP server module. Optional: derived from BASE_DIR when unset.
MCP_SERVER_MODULE = os.getenv("MCP_SERVER_MODULE", "yatrip.mcp_server")
MCP_SERVER_TIMEOUT = float(os.getenv("MCP_SERVER_TIMEOUT", "60"))


# ---------------------------------------------------------------------------
# Native geospatial libraries
# ---------------------------------------------------------------------------
# GDAL/GEOS ship outside pip on Windows, so their location is machine specific.
# Point GDAL_LIBRARY_PATH / GEOS_LIBRARY_PATH at your install, or append
# GDAL_BIN_PATH to PATH and let Django discover the DLLs.

GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH", "") or None
GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH", "") or None

for _bin_env_key in ("GDAL_BIN_PATH", "GEOS_BIN_PATH"):
    _bin_dir = os.getenv(_bin_env_key)
    if _bin_dir and os.path.isdir(_bin_dir) and _bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + _bin_dir


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # token_blacklist must be installed for SIMPLE_JWT BLACKLIST_AFTER_ROTATION
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "rest_framework_gis",
    "pgvector.django",
    # Project apps
    "accounts",
    "hotels",
    "rentals",
    "food",
    "reviews",
    "api_keys",
    "attractions",
    "transport",
    "chatbot",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must sit above anything that can generate a response,
    # otherwise CORS headers go missing from error and redirect replies.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "yatrip.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "yatrip.wsgi.application"
ASGI_APPLICATION = "yatrip.asgi.application"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# Cache / Redis
# ---------------------------------------------------------------------------
# Redis is used when it is actually reachable, and the process silently falls
# back to a local memory cache when it is not. That is deliberate: Redis is not
# reachable in every environment this runs in (there is no native Redis on
# Windows without WSL or a container), and a cache backend that throws at
# import time takes the whole API down for a component that only exists to save
# time. Caching is an optimisation here, never a correctness requirement, so it
# must never be able to break a request.

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "yatrip-default",
        "TIMEOUT": 300,
    }
}


def _redis_reachable(url: str) -> bool:
    """One cheap TCP probe, run once at import."""
    try:
        from urllib.parse import urlparse

        import socket

        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except Exception:  # noqa: BLE001 - any failure means "not available"
        return False


REDIS_AVAILABLE = _redis_reachable(REDIS_URL)

if REDIS_AVAILABLE:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
        "OPTIONS": {
            # Connections must not outlive the worker; a dead cached socket
            # otherwise surfaces as a hang on the first request that misses.
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
        },
    }
else:
    # Kept as a named alias so operational tooling can still address it.
    CACHES["fallback"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "yatrip-fallback",
    }

#: Cache TTLs, in one place so a value is not magic in a view.
CACHE_TTL_NEARBY = int(os.getenv("CACHE_TTL_NEARBY", "300"))
CACHE_TTL_ROUTE = int(os.getenv("CACHE_TTL_ROUTE", "86400"))
CACHE_TTL_GEOCODE = int(os.getenv("CACHE_TTL_GEOCODE", "604800"))

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL if REDIS_AVAILABLE else "memory://"
CELERY_RESULT_BACKEND = REDIS_URL if REDIS_AVAILABLE else "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = not REDIS_AVAILABLE
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Cookie first, header second. The cookie path is what a browser app
        # uses, where a JS-readable token would be readable by any injected
        # script; the header is kept for CLI tools and the test client.
        "yatrip.auth.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
    # Backed by the cache below, so with Redis up this is a shared, atomic
    # counter across processes; with the fallback it degrades to per-process
    # rather than failing open.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "120/hour"),
        "user": os.getenv("THROTTLE_USER", "1000/hour"),
        # Expensive upstream sync: a single request can fan out into dozens of
        # Overpass calls, so it gets its own, much tighter budget.
        "sync": os.getenv("THROTTLE_SYNC", "10/hour"),
        # Food OSM import. Separate from "sync" because browsing food is a plain
        # database read and must not spend this budget.
        "food_import": os.getenv("THROTTLE_FOOD_IMPORT", "20/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTES", "300"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
