"""Account models — Organization, UserProfile."""

import hashlib
import secrets

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Multi-tenant organization."""

    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
        ("team", "Team"),
        ("enterprise", "Enterprise"),
    ]

    PLAN_LIMITS = {
        "free": {"projects": 3, "history_days": 30, "seats": 1},
        "pro": {"projects": 0, "history_days": 365, "seats": 1},
        "team": {"projects": 0, "history_days": 0, "seats": 10},
        "enterprise": {"projects": 0, "history_days": 0, "seats": 0},
    }

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    stripe_customer_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_orgs",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.plan})"

    @property
    def limits(self):
        return self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS["free"])

    @property
    def project_limit(self):
        return self.limits["projects"]

    @property
    def history_days(self):
        return self.limits["history_days"]

    @property
    def seat_limit(self):
        return self.limits["seats"]


class UserProfile(models.Model):
    """Extended user profile linked to Organization."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    github_username = models.CharField(max_length=200, blank=True)
    avatar_url = models.CharField(max_length=500, blank=True)
    api_key_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} ({self.github_username or 'no github'})"

    def generate_api_key(self):
        """Generate a new API key. Returns plaintext (shown once)."""
        plaintext = f"ck_{secrets.token_urlsafe(32)}"
        self.api_key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        self.save(update_fields=["api_key_hash"])
        return plaintext

    def verify_api_key(self, plaintext):
        """Check if plaintext key matches stored hash."""
        if not self.api_key_hash:
            return False
        return hashlib.sha256(plaintext.encode()).hexdigest() == self.api_key_hash
