"""Admin registration for accounts models."""

from django.contrib import admin

from apps.accounts.models import Organization, UserProfile


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "plan", "owner", "created_at"]
    list_filter = ["plan"]
    search_fields = ["name", "slug"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "org", "github_username", "created_at"]
    search_fields = ["user__email", "github_username"]
