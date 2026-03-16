"""Admin registration for billing models."""

from django.contrib import admin

from apps.billing.models import Subscription, UsageRecord


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["org", "plan", "current_period_end", "cancel_at_period_end"]
    list_filter = ["plan"]


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ["org", "month", "handoff_count", "session_count", "api_call_count"]
    list_filter = ["month"]
