"""Local development settings."""

from .base import *  # noqa: F401,F403

from decouple import config

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

import dj_database_url

_db_url = config("DATABASE_URL", default="")
_use_pg = False

if _db_url and _db_url.startswith("postgres"):
    try:
        import psycopg2
        conn = psycopg2.connect(_db_url, connect_timeout=2)
        conn.close()
        _use_pg = True
    except Exception:
        _use_pg = False

if _use_pg:
    DATABASES = {"default": dj_database_url.parse(_db_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# Show browsable API in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
