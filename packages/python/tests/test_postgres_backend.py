"""Tests for PostgresBackend — skipped if VAULTIT_DATABASE_URL not set."""

from __future__ import annotations

import os

import pytest

# Skip entire module if no database URL
pytestmark = pytest.mark.skipif(
    not os.environ.get("VAULTIT_DATABASE_URL"),
    reason="VAULTIT_DATABASE_URL not set",
)


from vaultit.backends.postgres import PostgresBackend
from vaultit.exceptions import (
    BackendError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
    SessionNotFoundError,
)
from vaultit.models import (
    AgentType,
    AuditEvent,
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
    Task,
    TaskStatus,
    Decision,
)


@pytest.fixture
def backend():
    b = PostgresBackend()
    # Clean tables for test isolation
    conn = b._get_conn()
    try:
        with conn.cursor() as cur:
            for table in ("handoffs", "locks", "audit_events", "api_keys", "sessions", "projects"):
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        b._put_conn(conn)
    b._initialized = False
    return b


@pytest.fixture
def config() -> ProjectConfig:
    return ProjectConfig(
        project_id="test-pg",
        name="Test PG",
        backend="postgres",
    )


@pytest.fixture
def initialized(backend: PostgresBackend, config: ProjectConfig) -> PostgresBackend:
    backend.init_project(config)
    return backend


class TestInitProject:
    def test_creates_tables(self, backend: PostgresBackend, config: ProjectConfig):
        backend.init_project(config)
        assert backend.project_exists(config.project_id)

    def test_config_round_trip(self, initialized: PostgresBackend, config: ProjectConfig):
        read = initialized.read_config()
        assert read.project_id == config.project_id
        assert read.name == config.name

    def test_idempotent(self, backend: PostgresBackend, config: ProjectConfig):
        backend.init_project(config)
        backend.init_project(config)
        assert backend.project_exists(config.project_id)


class TestProjectExists:
    def test_false_before_init(self, backend: PostgresBackend):
        assert backend.project_exists("nonexistent") is False

    def test_true_after_init(self, initialized: PostgresBackend, config: ProjectConfig):
        assert initialized.project_exists(config.project_id)


class TestSessions:
    def test_write_and_read(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id, agent=AgentType.claude)
        initialized.write_session(s)
        read = initialized.read_session(s.id)
        assert read.id == s.id
        assert read.agent == AgentType.claude

    def test_read_missing_raises(self, initialized: PostgresBackend):
        with pytest.raises(SessionNotFoundError):
            initialized.read_session("nonexistent")

    def test_list_sessions(self, initialized: PostgresBackend, config: ProjectConfig):
        s1 = Session(project_id=config.project_id)
        s2 = Session(project_id=config.project_id)
        initialized.write_session(s1)
        initialized.write_session(s2)
        sessions = initialized.list_sessions(config.project_id)
        assert len(sessions) == 2


class TestHandoffs:
    def _write_handoff(self, backend, config, session_id, version=1, tasks=None):
        h = Handoff(
            session_id=session_id,
            project_id=config.project_id,
            version=version,
            tasks=tasks or [],
        )
        backend.write_handoff(h)
        return h

    def test_write_and_read(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id)
        initialized.write_session(s)
        h = self._write_handoff(initialized, config, s.id)
        read = initialized.read_handoff(s.id, version=1)
        assert read.version == 1

    def test_read_latest_version(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id)
        initialized.write_session(s)
        self._write_handoff(initialized, config, s.id, version=1)
        self._write_handoff(initialized, config, s.id, version=2)
        read = initialized.read_handoff(s.id)
        assert read.version == 2

    def test_read_missing_session_raises(self, initialized: PostgresBackend):
        with pytest.raises(HandoffNotFoundError):
            initialized.read_handoff("nonexistent")

    def test_read_missing_version_raises(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id)
        initialized.write_session(s)
        self._write_handoff(initialized, config, s.id, version=1)
        with pytest.raises(HandoffNotFoundError):
            initialized.read_handoff(s.id, version=999)

    def test_read_latest_handoff_across_sessions(self, initialized: PostgresBackend, config: ProjectConfig):
        s1 = Session(project_id=config.project_id)
        s2 = Session(project_id=config.project_id)
        initialized.write_session(s1)
        initialized.write_session(s2)
        self._write_handoff(initialized, config, s1.id, version=1)
        import time
        time.sleep(0.01)
        self._write_handoff(initialized, config, s2.id, version=1)
        latest = initialized.read_latest_handoff(config.project_id)
        assert latest is not None
        assert latest.session_id == s2.id

    def test_read_latest_handoff_none_when_empty(self, initialized: PostgresBackend, config: ProjectConfig):
        assert initialized.read_latest_handoff(config.project_id) is None

    def test_jsonb_roundtrip(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id)
        initialized.write_session(s)
        tasks = [Task(id="TASK-0001", title="Alpha", status=TaskStatus.in_progress)]
        decisions = [Decision(id="DEC-0001", summary="Use postgres")]
        h = Handoff(
            session_id=s.id,
            project_id=config.project_id,
            version=1,
            tasks=tasks,
            decisions=decisions,
            open_questions=["Why?"],
            next_steps=["Step 1"],
            metadata={"key": "value"},
        )
        initialized.write_handoff(h)
        read = initialized.read_handoff(s.id, version=1)
        assert len(read.tasks) == 1
        assert read.tasks[0].id == "TASK-0001"
        assert read.tasks[0].status == TaskStatus.in_progress
        assert len(read.decisions) == 1
        assert read.open_questions == ["Why?"]
        assert read.metadata == {"key": "value"}


class TestDiff:
    def test_diff_detects_added_tasks(self, initialized: PostgresBackend, config: ProjectConfig):
        s = Session(project_id=config.project_id)
        initialized.write_session(s)
        h1 = Handoff(session_id=s.id, project_id=config.project_id, version=1, tasks=[])
        h2 = Handoff(
            session_id=s.id, project_id=config.project_id, version=2,
            tasks=[Task(id="TASK-0001", title="New")],
        )
        initialized.write_handoff(h1)
        initialized.write_handoff(h2)
        d = initialized.diff(config.project_id, 1, 2)
        assert len(d.tasks_added) == 1

    def test_diff_not_found(self, initialized: PostgresBackend, config: ProjectConfig):
        with pytest.raises(HandoffNotFoundError):
            initialized.diff(config.project_id, 1, 2)


class TestAuditEvent:
    def test_audit_event_write(self, initialized: PostgresBackend, config: ProjectConfig):
        event = AuditEvent(
            project_id=config.project_id,
            action="sync",
            agent="claude",
            metadata={"version": 1},
        )
        initialized.add_audit_event(event)
        # Verify by reading back
        conn = initialized._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM audit_events WHERE project_id = %s", (config.project_id,))
                count = cur.fetchone()[0]
            conn.commit()
            assert count == 1
        finally:
            initialized._put_conn(conn)


class TestConnectionPool:
    def test_connection_pool_health(self, initialized: PostgresBackend):
        assert initialized.ping() is True


class TestErrorHandling:
    def test_operations_fail_before_init(self, backend: PostgresBackend):
        with pytest.raises(ProjectNotInitializedError):
            backend.read_config()
