"""URL patterns for billing app."""

from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("plans/", views.plans_view, name="plans"),
]
