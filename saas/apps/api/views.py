"""DRF API views for vaultit SaaS."""

from uuid import uuid4

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Organization, UserProfile
from apps.accounts.serializers import UserProfileSerializer
from apps.projects.models import Handoff, Project, Session
from apps.projects.serializers import (
    DecisionCreateSerializer,
    HandoffCreateSerializer,
    HandoffSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
    SessionCreateSerializer,
    SessionSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
)


def _get_org(user):
    """Get user's org, creating default if needed."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.org is None:
        org = Organization.objects.create(
            name=f"{user.email}'s org",
            slug=f"user-{user.pk}",
            owner=user,
        )
        profile.org = org
        profile.save(update_fields=["org"])
    return profile.org


def _get_project(user, project_id):
    """Get project scoped to user's org."""
    org = _get_org(user)
    return get_object_or_404(Project, project_id=project_id, org=org)


def _slugify(name):
    return name.lower().replace(" ", "-").replace("_", "-")


# ── Projects ──


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_list(request):
    org = _get_org(request.user)
    if request.method == "GET":
        projects = Project.objects.filter(org=org)
        return Response(ProjectSerializer(projects, many=True).data)
    ser = ProjectCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    project = Project.objects.create(
        project_id=_slugify(ser.validated_data["name"]),
        name=ser.validated_data["name"],
        org=org,
        owner=request.user,
        coordination=ser.validated_data.get("coordination", "sequential"),
    )
    return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def project_detail(request, project_id):
    project = _get_project(request.user, project_id)
    if request.method == "DELETE":
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(ProjectSerializer(project).data)


# ── Sessions ──


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def session_list(request, project_id):
    project = _get_project(request.user, project_id)
    if request.method == "GET":
        sessions = Session.objects.filter(project=project)
        return Response(SessionSerializer(sessions, many=True).data)
    ser = SessionCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    session = Session.objects.create(
        session_id=uuid4().hex[:12],
        project=project,
        agent=ser.validated_data.get("agent", "custom"),
        user=request.user,
    )
    return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def session_detail(request, project_id, session_id):
    project = _get_project(request.user, project_id)
    session = get_object_or_404(Session, session_id=session_id, project=project)
    if request.method == "DELETE":
        session.closed_at = timezone.now()
        session.save(update_fields=["closed_at"])
        return Response(SessionSerializer(session).data)
    return Response(SessionSerializer(session).data)


# ── Handoffs ──


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def handoff_list(request, project_id, session_id):
    project = _get_project(request.user, project_id)
    session = get_object_or_404(Session, session_id=session_id, project=project)
    if request.method == "GET":
        handoffs = Handoff.objects.filter(session=session)
        return Response(HandoffSerializer(handoffs, many=True).data)
    ser = HandoffCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    latest_version = Handoff.objects.filter(session=session).order_by("-version").values_list("version", flat=True).first()
    version = (latest_version or 0) + 1
    handoff = Handoff.objects.create(
        handoff_id=uuid4().hex[:12],
        session=session,
        version=version,
        agent=d.get("agent", "custom"),
        agent_version=d.get("agent_version", ""),
        tasks=d.get("tasks", []),
        decisions=d.get("decisions", []),
        open_questions=d.get("open_questions", []),
        next_steps=d.get("next_steps", []),
        raw_notes=d.get("notes", ""),
    )
    return Response(HandoffSerializer(handoff).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def handoff_detail(request, project_id, session_id, version):
    project = _get_project(request.user, project_id)
    session = get_object_or_404(Session, session_id=session_id, project=project)
    handoff = get_object_or_404(Handoff, session=session, version=version)
    return Response(HandoffSerializer(handoff).data)


# ── Bootstrap ──


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bootstrap(request, project_id):
    project = _get_project(request.user, project_id)
    latest = (
        Handoff.objects.filter(session__project=project)
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return Response({"briefing": f"Project '{project.name}' has no handoffs yet."})
    lines = [
        f"== vaultit bootstrap ==",
        f"Project: {project.name} ({project.project_id})",
        f"Session: {latest.session.session_id}",
        f"Version: v{latest.version}",
        f"Agent: {latest.agent}",
    ]
    if latest.tasks:
        lines.append(f"\nTasks ({len(latest.tasks)}):")
        for t in latest.tasks:
            lines.append(f"  [{t.get('status', 'pending')}] {t.get('id', '?')}: {t.get('title', '?')}")
    if latest.next_steps:
        lines.append(f"\nNext steps:")
        for s in latest.next_steps:
            lines.append(f"  - {s}")
    if latest.open_questions:
        lines.append(f"\nOpen questions:")
        for q in latest.open_questions:
            lines.append(f"  ? {q}")
    if latest.raw_notes:
        lines.append(f"\nNotes: {latest.raw_notes}")
    return Response({"briefing": "\n".join(lines)})


# ── Tasks ──


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_create(request, project_id):
    project = _get_project(request.user, project_id)
    ser = TaskCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    latest = (
        Handoff.objects.filter(session__project=project)
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return Response({"detail": "No handoffs yet."}, status=status.HTTP_404_NOT_FOUND)
    tasks = [t for t in latest.tasks if t.get("id") != d["task_id"]]
    tasks.append({"id": d["task_id"], "title": d["title"], "status": d["status"], "owner": d["owner"]})
    new_handoff = Handoff.objects.create(
        handoff_id=uuid4().hex[:12],
        session=latest.session,
        version=latest.version + 1,
        agent=latest.agent,
        tasks=tasks,
        decisions=latest.decisions,
        open_questions=latest.open_questions,
        next_steps=latest.next_steps,
        raw_notes=latest.raw_notes,
    )
    return Response(HandoffSerializer(new_handoff).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def task_update(request, project_id, task_id):
    project = _get_project(request.user, project_id)
    ser = TaskUpdateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    latest = (
        Handoff.objects.filter(session__project=project)
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return Response({"detail": "No handoffs yet."}, status=status.HTTP_404_NOT_FOUND)
    found = False
    tasks = []
    for t in latest.tasks:
        if t.get("id") == task_id:
            found = True
            t["status"] = ser.validated_data["status"]
        tasks.append(t)
    if not found:
        return Response({"detail": f"Task '{task_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
    new_handoff = Handoff.objects.create(
        handoff_id=uuid4().hex[:12],
        session=latest.session,
        version=latest.version + 1,
        agent=latest.agent,
        tasks=tasks,
        decisions=latest.decisions,
        open_questions=latest.open_questions,
        next_steps=latest.next_steps,
        raw_notes=latest.raw_notes,
    )
    return Response(HandoffSerializer(new_handoff).data)


# ── Decisions ──


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decision_create(request, project_id):
    project = _get_project(request.user, project_id)
    ser = DecisionCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    latest = (
        Handoff.objects.filter(session__project=project)
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return Response({"detail": "No handoffs yet."}, status=status.HTTP_404_NOT_FOUND)
    decisions = list(latest.decisions) + [{
        "id": d["decision_id"], "summary": d["summary"],
        "rationale": d.get("rationale", ""), "made_by": d.get("made_by", "human"),
    }]
    new_handoff = Handoff.objects.create(
        handoff_id=uuid4().hex[:12],
        session=latest.session,
        version=latest.version + 1,
        agent=latest.agent,
        tasks=latest.tasks,
        decisions=decisions,
        open_questions=latest.open_questions,
        next_steps=latest.next_steps,
        raw_notes=latest.raw_notes,
    )
    return Response(HandoffSerializer(new_handoff).data, status=status.HTTP_201_CREATED)


# ── Auth ──


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_me(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return Response(UserProfileSerializer(profile).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def auth_keys(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        plaintext = profile.generate_api_key()
        return Response({
            "key": plaintext,
            "message": "Save this key now. It will not be shown again.",
        }, status=status.HTTP_201_CREATED)
    has_key = bool(profile.api_key_hash)
    return Response({"has_key": has_key})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def auth_key_delete(request, key_id):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.api_key_hash = ""
    profile.save(update_fields=["api_key_hash"])
    return Response({"detail": "API key revoked."})


# ── Billing ──


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_usage(request):
    org = _get_org(request.user)
    from apps.billing.models import UsageRecord
    records = UsageRecord.objects.filter(org=org).order_by("-month")[:12]
    data = [
        {
            "month": r.month.isoformat(),
            "handoffs": r.handoff_count,
            "sessions": r.session_count,
            "api_calls": r.api_call_count,
        }
        for r in records
    ]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_plans(request):
    plans = [
        {
            "name": "Free",
            "slug": "free",
            "price": 0,
            "projects": 3,
            "history_days": 30,
            "seats": 1,
        },
        {
            "name": "Pro",
            "slug": "pro",
            "price": 19,
            "projects": "unlimited",
            "history_days": 365,
            "seats": 1,
        },
        {
            "name": "Team",
            "slug": "team",
            "price": 49,
            "projects": "unlimited",
            "history_days": "unlimited",
            "seats": 10,
        },
        {
            "name": "Enterprise",
            "slug": "enterprise",
            "price": "custom",
            "projects": "unlimited",
            "history_days": "unlimited",
            "seats": "unlimited",
        },
    ]
    return Response(plans)
