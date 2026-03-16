"""Tests for vaultit.models — Pydantic validation, enums, defaults."""

from datetime import datetime, timezone

import pytest

from vaultit.models import (
    AgentType,
    Decision,
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
    Task,
    TaskStatus,
)


# ── TaskStatus enum ──


class TestTaskStatus:
    def test_values(self):
        assert set(TaskStatus) == {
            TaskStatus.pending,
            TaskStatus.in_progress,
            TaskStatus.done,
            TaskStatus.blocked,
        }

    def test_string_coercion(self):
        assert TaskStatus("pending") == TaskStatus.pending
        assert TaskStatus("in_progress") == TaskStatus.in_progress


# ── AgentType enum ──


class TestAgentType:
    def test_values(self):
        assert set(AgentType) == {
            AgentType.claude,
            AgentType.gpt,
            AgentType.gemini,
            AgentType.custom,
        }

    def test_string_coercion(self):
        assert AgentType("claude") == AgentType.claude


# ── Task ──


class TestTask:
    def test_valid_id(self):
        t = Task(id="TASK-0001", title="Do the thing")
        assert t.id == "TASK-0001"
        assert t.status == TaskStatus.pending
        assert t.owner == "human"
        assert t.depends_on == []
        assert t.notes == ""

    def test_invalid_id_rejected(self):
        with pytest.raises(ValueError, match="TASK-XXXX"):
            Task(id="bad-id", title="Nope")

    def test_invalid_id_format(self):
        with pytest.raises(ValueError):
            Task(id="TASK-1", title="Too short")

    def test_all_fields(self):
        t = Task(
            id="TASK-0042",
            title="Build widget",
            status="done",
            owner="claude",
            depends_on=["TASK-0001"],
            notes="Completed in v2",
        )
        assert t.status == TaskStatus.done
        assert t.depends_on == ["TASK-0001"]


# ── Decision ──


class TestDecision:
    def test_valid_id(self):
        d = Decision(id="DEC-0001", summary="Use Pydantic v2")
        assert d.id == "DEC-0001"
        assert d.rationale == ""
        assert d.made_by == "human"
        assert d.supersedes is None
        assert isinstance(d.made_at, datetime)

    def test_invalid_id(self):
        with pytest.raises(ValueError, match="DEC-XXXX"):
            Decision(id="DEC-1", summary="Bad")

    def test_supersedes(self):
        d = Decision(id="DEC-0002", summary="Switch to SQLite", supersedes="DEC-0001")
        assert d.supersedes == "DEC-0001"


# ── Handoff ──


class TestHandoff:
    def test_defaults(self):
        h = Handoff(session_id="abc123", project_id="myproject")
        assert h.version == 1
        assert h.schema_version == "1.0"
        assert h.agent == AgentType.custom
        assert h.tasks == []
        assert h.decisions == []
        assert h.open_questions == []
        assert h.next_steps == []
        assert h.raw_notes == ""
        assert h.metadata == {}
        assert isinstance(h.id, str)
        assert len(h.id) > 0

    def test_roundtrip_json(self):
        h = Handoff(
            session_id="s1",
            project_id="p1",
            tasks=[Task(id="TASK-0001", title="Test")],
            decisions=[Decision(id="DEC-0001", summary="Yes")],
        )
        data = h.model_dump(mode="json")
        h2 = Handoff.model_validate(data)
        assert h2.tasks[0].id == "TASK-0001"
        assert h2.decisions[0].summary == "Yes"


# ── Session ──


class TestSession:
    def test_defaults(self):
        s = Session(project_id="myproject")
        assert isinstance(s.id, str)
        assert s.closed_at is None
        assert s.agent == AgentType.custom
        assert s.user_id == ""


# ── ProjectConfig ──


class TestProjectConfig:
    def test_defaults(self):
        c = ProjectConfig(project_id="test", name="Test Project")
        assert c.backend == "file"
        assert c.coordination == "sequential"
        assert c.schema_version == "1.0"

    def test_invalid_coordination(self):
        with pytest.raises(ValueError, match="coordination"):
            ProjectConfig(project_id="x", name="X", coordination="invalid")

    def test_valid_coordination_modes(self):
        for mode in ("sequential", "lock", "merge"):
            c = ProjectConfig(project_id="x", name="X", coordination=mode)
            assert c.coordination == mode


# ── HandoffDiff ──


class TestHandoffDiff:
    def test_empty_diff(self):
        d = HandoffDiff(from_version=1, to_version=2)
        assert d.tasks_added == []
        assert d.tasks_removed == []
        assert d.tasks_changed == []
        assert d.decisions_added == []
        assert d.questions_added == []
        assert d.next_steps_changed == []
