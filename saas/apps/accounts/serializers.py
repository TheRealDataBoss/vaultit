"""DRF serializers for accounts."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.models import Organization, UserProfile

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "plan", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    org = OrganizationSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["email", "github_username", "avatar_url", "org", "created_at"]
        read_only_fields = ["created_at"]
