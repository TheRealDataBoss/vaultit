"""Billing views — plan comparison page."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def plans_view(request):
    plans = [
        {"name": "Free", "slug": "free", "price": "$0", "projects": "3", "history": "30 days", "seats": "1"},
        {"name": "Pro", "slug": "pro", "price": "$19/mo", "projects": "Unlimited", "history": "1 year", "seats": "1"},
        {"name": "Team", "slug": "team", "price": "$49/mo", "projects": "Unlimited", "history": "Unlimited", "seats": "10"},
        {"name": "Enterprise", "slug": "enterprise", "price": "Custom", "projects": "Unlimited", "history": "Unlimited", "seats": "Unlimited"},
    ]
    return render(request, "billing/plans.html", {"plans": plans})
