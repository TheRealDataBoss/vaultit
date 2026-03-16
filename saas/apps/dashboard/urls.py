"""URL patterns for dashboard app."""

from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("projects/<str:project_id>/", views.project_detail, name="project-detail"),
    path("projects/<str:project_id>/sessions/<str:session_id>/", views.session_detail, name="session-detail"),
]
