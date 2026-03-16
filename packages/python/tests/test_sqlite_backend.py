"""Tests for SQLiteBackend — mirrors test_file_backend.py structure."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from vaultit.backends.sqlite import SQLiteBackend
from vaultit.exceptions import (
    BackendError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
    SessionNotFoundError,
)
from vaultit.models import (
    AgentType,
    Decision,
    Handoff,
    ProjectConfig,
    Session,
    Task,
    TaskStatus,
)


@pytest.fixture
def backend(tmp_path: Path) -> SQLiteBackend:
    return SQLiteBackend(root=tmp_path)


@pytest.fixture
def initialized_backend(backend: SQLiteBackend) -> SQLiteBackend:
    config = ProjectConfig(project_id="test-project", name="Test Project")
    backend.init_project(config)
    return backend


# ── init_project ──


class TestInitProject:
    def test_creates_db(self, backend: SQLiteBackend, tmp_path: Path):
        config = ProjectConfig(project_id="myproj", name="My Project")
        backend.init_project(config)
        assert backend.db_path.is_file()
        assert (tmp_path / ".vaultit" / "config.json").is_file()

    def test_config_round_trip(self, backend: SQLiteBackend):
        config = ProjectConfig(
            project_id="roundtrip",
            name="Round Trip",
            coordination="lock",
        )
        backend.init_project(config)
        loaded = backend.read_config()
        assert loaded.project_id == "roundtrip"
        assert loaded.name == "Round Trip"
        assert loaded.coordination == "lock"

    def test_idempotent(self, backend: SQLiteBackend):
        config = ProjectConfig(project_id="idem", name="Idempotent")
        backend.init_project(config)
        backend.init_project(config)  # should not raise
        assert backend.read_config().project_id == "idem"


# ── project_exists ──


class TestProjectExists:
    def test_false_before_init(self, backend: SQLiteBackend):
        assert not backend.project_exists("anything")

    def test_true_after_init(self, initialized_backend: SQLiteBackend):
        assert initialized_backend.project_exists("test-project")

    def test_false_for_wrong_id(self, initialized_backend: SQLiteBackend):
        assert not initialized_backend.project_exists("other-project")


# ── write/read session ──


class TestSessions:
    def test_write_and_read(self, initialized_backend: SQLiteBackend):
        session = Session(id="sess-001", project_id="test-project")
        initialized_backend.write_session(session)
        loaded = initialized_backend.read_session("sess-001")
        assert loaded.id == "sess-001"
        assert loaded.project_id == "test-project"

    def test_read_missing_raises(self, initialized_backend: SQLiteBackend):
        with pytest.raises(SessionNotFoundError):
            initialized_backend.read_session("nonexistent")

    def test_list_sessions(self, initialized_backend: SQLiteBackend):
        s1 = Session(id="s1", project_id="test-project")
        s2 = Session(id="s2", project_id="test-project")
        s3 = Session(id="s3", project_id="other-project")
        initialized_backend.write_session(s1)
        initialized_backend.write_session(s2)
        initialized_backend.write_session(s3)

        sessions = initialized_backend.list_sessions("test-project")
        assert len(sessions) == 2
        assert {s.id for s in sessions} == {"s1", "s2"}


# ── write/read handoff ──


class TestHandoffs:
    def test_write_and_read(self, initialized_backend: SQLiteBackend):
        handoff = Handoff(
            session_id="sess-a",
            project_id="test-project",
            version=1,
            tasks=[Task(id="TASK-0001", title="First task")],
        )
        hid = initialized_backend.write_handoff(handoff)
        assert isinstance(hid, str)

        loaded = initialized_backend.read_handoff("sess-a", version=1)
        assert loaded.version == 1
        assert loaded.tasks[0].id == "TASK-0001"

    def test_read_latest_version(self, initialized_backend: SQLiteBackend):
        for v in (1, 2, 3):
            h = Handoff(
                session_id="sess-b",
                project_id="test-project",
                version=v,
                raw_notes=f"v{v}",
            )
            initialized_backend.write_handoff(h)

        latest = initialized_backend.read_handoff("sess-b")
        assert latest.version == 3
        assert latest.raw_notes == "v3"

    def test_read_missing_session_raises(self, initialized_backend: SQLiteBackend):
        with pytest.raises(HandoffNotFoundError):
            initialized_backend.read_handoff("no-such-session")

    def test_read_missing_version_raises(self, initialized_backend: SQLiteBackend):
        h = Handoff(session_id="sess-c", project_id="test-project", version=1)
        initialized_backend.write_handoff(h)
        with pytest.raises(HandoffNotFoundError):
            initialized_backend.read_handoff("sess-c", version=99)

    def test_read_latest_handoff_across_sessions(self, initialized_backend: SQLiteBackend):
        t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2025, 6, 1, tzinfo=timezone.utc)

        h1 = Handoff(
            session_id="old-sess",
            project_id="test-project",
            version=1,
            updated_at=t1,
        )
        h2 = Handoff(
            session_id="new-sess",
            project_id="test-project",
            version=1,
            updated_at=t2,
        )
        initialized_backend.write_handoff(h1)
        initialized_backend.write_handoff(h2)

        latest = initialized_backend.read_latest_handoff("test-project")
        assert latest is not None
        assert latest.session_id == "new-sess"

    def test_read_latest_handoff_none_when_empty(self, initialized_backend: SQLiteBackend):
        assert initialized_backend.read_latest_handoff("test-project") is None


# ── versioning ──


class TestVersioning:
    def test_versions_are_independent(self, initialized_backend: SQLiteBackend):
        for v in range(1, 4):
            h = Handoff(
                session_id="versioned",
                project_id="test-project",
                version=v,
            )
            initialized_backend.write_handoff(h)

        for v in range(1, 4):
            h = initialized_backend.read_handoff("versioned", version=v)
            assert h.version == v


# ── diff ──


class TestDiff:
    def test_diff_detects_added_tasks(self, initialized_backend: SQLiteBackend):
        h1 = Handoff(
            session_id="diff-sess",
            project_id="test-project",
            version=1,
            tasks=[],
        )
        h2 = Handoff(
            session_id="diff-sess",
            project_id="test-project",
            version=2,
            tasks=[Task(id="TASK-0001", title="New task")],
        )
        initialized_backend.write_handoff(h1)
        initialized_backend.write_handoff(h2)

        d = initialized_backend.diff("test-project", 1, 2)
        assert d.from_version == 1
        assert d.to_version == 2
        assert len(d.tasks_added) == 1
        assert d.tasks_added[0].id == "TASK-0001"

    def test_diff_detects_removed_tasks(self, initialized_backend: SQLiteBackend):
        h1 = Handoff(
            session_id="diff-rem",
            project_id="test-project",
            version=1,
            tasks=[Task(id="TASK-0001", title="Will be removed")],
        )
        h2 = Handoff(
            session_id="diff-rem",
            project_id="test-project",
            version=2,
            tasks=[],
        )
        initialized_backend.write_handoff(h1)
        initialized_backend.write_handoff(h2)

        d = initialized_backend.diff("test-project", 1, 2)
        assert len(d.tasks_removed) == 1

    def test_diff_detects_changed_tasks(self, initialized_backend: SQLiteBackend):
        h1 = Handoff(
            session_id="diff-chg",
            project_id="test-project",
            version=1,
            tasks=[Task(id="TASK-0001", title="Original", status="pending")],
        )
        h2 = Handoff(
            session_id="diff-chg",
            project_id="test-project",
            version=2,
            tasks=[Task(id="TASK-0001", title="Original", status="done")],
        )
        initialized_backend.write_handoff(h1)
        initialized_backend.write_handoff(h2)

        d = initialized_backend.diff("test-project", 1, 2)
        assert len(d.tasks_changed) == 1
        assert d.tasks_changed[0].status == TaskStatus.done


# ── error handling ──


class TestErrorHandling:
    def test_operations_fail_before_init(self, backend: SQLiteBackend):
        with pytest.raises(ProjectNotInitializedError):
            backend.read_config()

    def test_read_session_not_found(self, initialized_backend: SQLiteBackend):
        with pytest.raises(SessionNotFoundError):
            initialized_backend.read_session("ghost")

    def test_handoff_with_complex_data_roundtrips(self, initialized_backend: SQLiteBackend):
        """Verify JSON serialization of nested lists/dicts survives SQLite storage."""
        h = Handoff(
            session_id="complex",
            project_id="test-project",
            version=1,
            tasks=[
                Task(id="TASK-0001", title="Build", status="done", depends_on=["TASK-0002"]),
            ],
            decisions=[
                Decision(id="DEC-0001", summary="Use SQLite", rationale="It's stdlib"),
            ],
            open_questions=["Should we add PostgreSQL?"],
            next_steps=["Write tests", "Deploy"],
            metadata={"priority": "high", "tags": ["backend", "v0.4"]},
        )
        initialized_backend.write_handoff(h)
        loaded = initialized_backend.read_handoff("complex", version=1)

        assert loaded.tasks[0].depends_on == ["TASK-0002"]
        assert loaded.decisions[0].rationale == "It's stdlib"
        assert loaded.open_questions == ["Should we add PostgreSQL?"]
        assert loaded.metadata["tags"] == ["backend", "v0.4"]
