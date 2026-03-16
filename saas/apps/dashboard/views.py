"""Dashboard views — HTMX-powered frontend."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import UserProfile
from apps.projects.models import Handoff, Project, Session


def index(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
    return render(request, "home.html")


def home_public(request):
    """Public landing page, always renders regardless of auth."""
    return render(request, "home.html")


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.org is None:
        from apps.accounts.models import Organization
        org = Organization.objects.create(
            name=f"{request.user.email}'s org",
            slug=f"user-{request.user.pk}",
            owner=request.user,
        )
        profile.org = org
        profile.save(update_fields=["org"])

    projects = Project.objects.filter(org=profile.org)
    project_count = projects.count()
    session_count = Session.objects.filter(project__org=profile.org).count()
    handoff_count = Handoff.objects.filter(session__project__org=profile.org).count()

    return render(request, "dashboard/index.html", {
        "projects": projects,
        "project_count": project_count,
        "session_count": session_count,
        "handoff_count": handoff_count,
        "profile": profile,
    })


@login_required
def project_detail(request, project_id):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    project = get_object_or_404(Project, project_id=project_id, org=profile.org)
    sessions = Session.objects.filter(project=project)
    recent_handoffs = Handoff.objects.filter(session__project=project).order_by("-created_at")[:10]

    return render(request, "dashboard/project_detail.html", {
        "project": project,
        "sessions": sessions,
        "recent_handoffs": recent_handoffs,
    })


@login_required
def session_detail(request, project_id, session_id):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    project = get_object_or_404(Project, project_id=project_id, org=profile.org)
    session = get_object_or_404(Session, session_id=session_id, project=project)
    handoffs = Handoff.objects.filter(session=session).order_by("-version")

    return render(request, "dashboard/session_detail.html", {
        "project": project,
        "session": session,
        "handoffs": handoffs,
    })
