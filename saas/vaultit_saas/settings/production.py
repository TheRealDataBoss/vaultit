"""Production settings."""

from .base import *  # noqa: F401,F403

from decouple import config

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="vaultit.ai", cast=lambda v: v.split(","))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="vaultit"),
        "USER": config("DB_USER", default="vaultit"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

_db_url = config("DATABASE_URL", default="")
if _db_url:
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(_db_url)

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
