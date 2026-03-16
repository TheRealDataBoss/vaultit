"""ASGI config for vaultit SaaS."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vaultit_saas.settings.production")

application = get_asgi_application()
