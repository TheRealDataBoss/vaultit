"""Admin registration for projects models."""

from django.contrib import admin

from apps.projects.models import Handoff, Project, Session


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "project_id", "org", "owner", "coordination", "created_at"]
    list_filter = ["coordination", "backend"]
    search_fields = ["name", "project_id"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["session_id", "project", "agent", "created_at", "closed_at"]
    list_filter = ["agent"]
    search_fields = ["session_id"]


@admin.register(Handoff)
class HandoffAdmin(admin.ModelAdmin):
    list_display = ["handoff_id", "session", "version", "agent", "created_at"]
    list_filter = ["agent"]
