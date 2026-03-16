"""Account views — settings page."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.models import UserProfile


@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    new_key = None

    if request.method == "POST" and "generate_key" in request.POST:
        new_key = profile.generate_api_key()

    return render(request, "accounts/settings.html", {
        "profile": profile,
        "new_key": new_key,
    })
