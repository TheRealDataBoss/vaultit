"""WSGI config for vaultit SaaS."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vaultit_saas.settings.production")

application = get_wsgi_application()
