"""Billing models — Subscription, UsageRecord."""

from django.db import models


class Subscription(models.Model):
    """Stripe subscription for an organization."""

    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
        ("team", "Team"),
        ("enterprise", "Enterprise"),
    ]

    org = models.OneToOneField(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    stripe_subscription_id = models.CharField(max_length=200, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.org.name} - {self.plan}"


class UsageRecord(models.Model):
    """Monthly usage tracking per organization."""

    org = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    month = models.DateField()
    handoff_count = models.IntegerField(default=0)
    session_count = models.IntegerField(default=0)
    api_call_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-month"]
        unique_together = [("org", "month")]
        indexes = [
            models.Index(fields=["org", "-month"]),
        ]

    def __str__(self):
        return f"{self.org.name} - {self.month.strftime('%Y-%m')}"
