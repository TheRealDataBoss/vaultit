"""API URL patterns — /api/v1/."""

from django.urls import path

from apps.api import views

app_name = "api"

urlpatterns = [
    # Projects
    path("projects/", views.project_list, name="project-list"),
    path("projects/<str:project_id>/", views.project_detail, name="project-detail"),

    # Sessions
    path("projects/<str:project_id>/sessions/", views.session_list, name="session-list"),
    path("projects/<str:project_id>/sessions/<str:session_id>/", views.session_detail, name="session-detail"),

    # Handoffs
    path("projects/<str:project_id>/sessions/<str:session_id>/handoffs/", views.handoff_list, name="handoff-list"),
    path("projects/<str:project_id>/sessions/<str:session_id>/handoffs/<int:version>/", views.handoff_detail, name="handoff-detail"),

    # Bootstrap
    path("projects/<str:project_id>/bootstrap/", views.bootstrap, name="bootstrap"),

    # Tasks
    path("projects/<str:project_id>/tasks/", views.task_create, name="task-create"),
    path("projects/<str:project_id>/tasks/<str:task_id>/", views.task_update, name="task-update"),

    # Decisions
    path("projects/<str:project_id>/decisions/", views.decision_create, name="decision-create"),

    # Auth
    path("auth/me/", views.auth_me, name="auth-me"),
    path("auth/keys/", views.auth_keys, name="auth-keys"),
    path("auth/keys/<str:key_id>/", views.auth_key_delete, name="auth-key-delete"),

    # Billing
    path("billing/usage/", views.billing_usage, name="billing-usage"),
    path("billing/plans/", views.billing_plans, name="billing-plans"),
]
