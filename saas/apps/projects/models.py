"""Project models — Project, Session, Handoff."""

from django.conf import settings
from django.db import models


class Project(models.Model):
    """A vaultit project owned by an organization."""

    project_id = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    org = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    backend = models.CharField(max_length=50, default="postgres")
    coordination = models.CharField(max_length=50, default="sequential")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project_id"]),
            models.Index(fields=["org"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.project_id})"


class Session(models.Model):
    """An agent session within a project."""

    session_id = models.CharField(max_length=200, unique=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    agent = models.CharField(max_length=100, default="custom")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["project"]),
        ]

    def __str__(self):
        status = "open" if self.closed_at is None else "closed"
        return f"{self.session_id[:12]} ({self.agent}, {status})"


class Handoff(models.Model):
    """A versioned handoff snapshot within a session."""

    handoff_id = models.CharField(max_length=200, unique=True)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="handoffs",
    )
    version = models.IntegerField()
    agent = models.CharField(max_length=100, default="custom")
    agent_version = models.CharField(max_length=100, blank=True)
    tasks = models.JSONField(default=list)
    decisions = models.JSONField(default=list)
    open_questions = models.JSONField(default=list)
    next_steps = models.JSONField(default=list)
    raw_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        unique_together = [("session", "version")]
        indexes = [
            models.Index(fields=["handoff_id"]),
            models.Index(fields=["session", "-version"]),
        ]

    def __str__(self):
        return f"v{self.version} ({self.session.session_id[:8]})"
