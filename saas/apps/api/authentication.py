"""DRF API key authentication for vaultit SaaS."""

import hashlib

from rest_framework import authentication, exceptions

from apps.accounts.models import UserProfile


class APIKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate via X-API-Key header against UserProfile.api_key_hash."""

    keyword = "X-API-Key"

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY", "")
        if not api_key:
            return None  # Let other authenticators try

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            profile = UserProfile.objects.select_related("user").get(
                api_key_hash=key_hash,
            )
        except UserProfile.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key.")

        if not profile.user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled.")

        return (profile.user, api_key)

    def authenticate_header(self, request):
        return self.keyword
