"""URL patterns for accounts app."""

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("", views.settings_view, name="settings"),
]
