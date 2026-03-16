"""Custom template context processors."""

APP_VERSION = "0.7.0"


def app_version(request):
    return {"app_version": APP_VERSION}
