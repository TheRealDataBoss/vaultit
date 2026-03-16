"""DRF permissions for vaultit SaaS API."""

from rest_framework import permissions


class IsProjectMember(permissions.BasePermission):
    """Allow access only to users whose org owns the project."""

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, "profile") or not request.user.profile:
            return False
        return obj.org_id == request.user.profile.org_id
