"""Pydantic v2 models for vaultit."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid4().hex[:12]


# ── Enums ──


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    blocked = "blocked"


class AgentType(str, Enum):
    claude = "claude"
    gpt = "gpt"
    gemini = "gemini"
    custom = "custom"


# ── Core models ──

_TASK_ID_RE = re.compile(r"^TASK-\d{4}$")
_DEC_ID_RE = re.compile(r"^DEC-\d{4}$")


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus = TaskStatus.pending
    owner: str = "human"
    depends_on: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("id")
    @classmethod
    def _validate_task_id(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(f"Task id must match TASK-XXXX, got '{v}'")
        return v


class Decision(BaseModel):
    id: str
    summary: str
    rationale: str = ""
    made_by: str = "human"
    made_at: datetime = Field(default_factory=_utcnow)
    supersedes: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_dec_id(cls, v: str) -> str:
        if not _DEC_ID_RE.match(v):
            raise ValueError(f"Decision id must match DEC-XXXX, got '{v}'")
        return v


class Handoff(BaseModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    project_id: str
    version: int = 1
    schema_version: str = "1.0"
    agent: AgentType = AgentType.custom
    agent_version: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    tasks: list[Task] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    raw_notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    id: str = Field(default_factory=_uuid)
    project_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    closed_at: datetime | None = None
    agent: AgentType = AgentType.custom
    user_id: str = ""


class ProjectConfig(BaseModel):
    project_id: str
    name: str
    created_at: datetime = Field(default_factory=_utcnow)
    backend: str = "file"
    coordination: str = "sequential"
    schema_version: str = "1.0"

    @field_validator("coordination")
    @classmethod
    def _validate_coordination(cls, v: str) -> str:
        allowed = {"sequential", "lock", "merge"}
        if v not in allowed:
            raise ValueError(f"coordination must be one of {allowed}, got '{v}'")
        return v


class HandoffDiff(BaseModel):
    from_version: int
    to_version: int
    tasks_added: list[Task] = Field(default_factory=list)
    tasks_removed: list[Task] = Field(default_factory=list)
    tasks_changed: list[Task] = Field(default_factory=list)
    decisions_added: list[Decision] = Field(default_factory=list)
    questions_added: list[str] = Field(default_factory=list)
    next_steps_changed: list[str] = Field(default_factory=list)


# ── Auth & multi-tenancy models ──


class ApiKey(BaseModel):
    id: str = Field(default_factory=_uuid)
    key_hash: str
    name: str
    user_id: str
    org_id: str = ""
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked: bool = False


class User(BaseModel):
    id: str = Field(default_factory=_uuid)
    email: str
    name: str = ""
    org_id: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    is_active: bool = True


class Organization(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    slug: str
    created_at: datetime = Field(default_factory=_utcnow)
    plan: str = "free"


class AuditEvent(BaseModel):
    id: str = Field(default_factory=_uuid)
    project_id: str
    session_id: str = ""
    user_id: str = ""
    org_id: str = ""
    action: str
    agent: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str = ""
