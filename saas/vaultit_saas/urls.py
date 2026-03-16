"""Root URL configuration for vaultit SaaS."""

from django.contrib import admin
from django.urls import include, path

from apps.dashboard.views import home_public, index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", include("apps.api.urls")),
    path("billing/", include("apps.billing.urls")),
    path("settings/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("home/", home_public, name="home"),
    path("", index, name="index"),
]
