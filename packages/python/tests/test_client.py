"""Tests for VaultItClient — full lifecycle with real FileBackend."""

from pathlib import Path

import pytest

from vaultit.client import VaultItClient
from vaultit.exceptions import ProjectNotInitializedError
from vaultit.models import AgentType, TaskStatus


@pytest.fixture
def client(tmp_path: Path) -> VaultItClient:
    return VaultItClient(project_dir=tmp_path)


@pytest.fixture
def initialized_client(client: VaultItClient) -> VaultItClient:
    client.init(name="Test Project")
    return client


# ── init ──


class TestInit:
    def test_creates_project(self, client: VaultItClient):
        config = client.init(name="My Project")
        assert config.project_id == "my-project"
        assert config.name == "My Project"
        assert config.coordination == "sequential"

    def test_custom_coordination(self, client: VaultItClient):
        config = client.init(name="Locked", coordination="lock")
        assert config.coordination == "lock"

    def test_slugifies_name(self, client: VaultItClient):
        config = client.init(name="My Cool Project")
        assert config.project_id == "my-cool-project"


# ── sync ──


class TestSync:
    def test_creates_handoff(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(notes="First sync")
        assert handoff.version == 1
        assert handoff.raw_notes == "First sync"
        assert handoff.agent == AgentType.custom

    def test_increments_version(self, initialized_client: VaultItClient):
        h1 = initialized_client.sync(notes="v1")
        h2 = initialized_client.sync(notes="v2")
        assert h1.version == 1
        assert h2.version == 2
        assert h1.session_id == h2.session_id  # same open session

    def test_with_tasks(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "Build it", "status": "pending"},
                {"id": "TASK-0002", "title": "Test it", "status": "done"},
            ],
        )
        assert len(handoff.tasks) == 2
        assert handoff.tasks[0].id == "TASK-0001"
        assert handoff.tasks[1].status == TaskStatus.done

    def test_with_decisions(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            decisions=[
                {"id": "DEC-0001", "summary": "Use Pydantic v2"},
            ],
        )
        assert len(handoff.decisions) == 1
        assert handoff.decisions[0].summary == "Use Pydantic v2"

    def test_with_agent(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(agent="claude", agent_version="3.5")
        assert handoff.agent == AgentType.claude
        assert handoff.agent_version == "3.5"

    def test_with_questions_and_next_steps(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            open_questions=["Should we use SQLite?"],
            next_steps=["Write tests", "Deploy"],
        )
        assert handoff.open_questions == ["Should we use SQLite?"]
        assert handoff.next_steps == ["Write tests", "Deploy"]

    def test_with_next_steps_only(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            next_steps=["Publish to PyPI", "Phase 2: SQLiteBackend"],
        )
        assert handoff.next_steps == ["Publish to PyPI", "Phase 2: SQLiteBackend"]
        assert handoff.open_questions == []

    def test_with_open_questions_only(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            open_questions=["Default backend?", "Support Python 3.9?"],
        )
        assert handoff.open_questions == ["Default backend?", "Support Python 3.9?"]
        assert handoff.next_steps == []

    def test_with_tasks_list(self, initialized_client: VaultItClient):
        handoff = initialized_client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "Init command", "status": "done"},
                {"id": "TASK-0002", "title": "Sync command", "status": "in_progress"},
                {"id": "TASK-0003", "title": "Bootstrap", "status": "pending"},
            ],
        )
        assert len(handoff.tasks) == 3
        assert handoff.tasks[0].status == TaskStatus.done
        assert handoff.tasks[1].status == TaskStatus.in_progress
        assert handoff.tasks[2].status == TaskStatus.pending


# ── bootstrap ──


class TestBootstrap:
    def test_no_handoffs_message(self, initialized_client: VaultItClient):
        output = initialized_client.bootstrap()
        assert "no handoffs" in output.lower()

    def test_renders_briefing(self, initialized_client: VaultItClient):
        initialized_client.sync(
            tasks=[{"id": "TASK-0001", "title": "Test task"}],
            notes="Important context",
        )
        output = initialized_client.bootstrap()
        assert "PROJECT BOOTSTRAP BRIEFING" in output
        assert "TASK-0001" in output
        assert "Test task" in output
        assert "Important context" in output


# ── status ──


class TestStatus:
    def test_empty_project(self, initialized_client: VaultItClient):
        result = initialized_client.status()
        assert result["project_id"] == "test-project"
        assert result["session_count"] == 0
        assert result["task_counts"] == {}
        assert "No handoffs" in result["latest_handoff"]

    def test_after_sync(self, initialized_client: VaultItClient):
        initialized_client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "A", "status": "pending"},
                {"id": "TASK-0002", "title": "B", "status": "done"},
                {"id": "TASK-0003", "title": "C", "status": "done"},
            ],
        )
        result = initialized_client.status()
        assert result["session_count"] == 1
        assert result["task_counts"]["pending"] == 1
        assert result["task_counts"]["done"] == 2


# ── doctor ──


class TestDoctor:
    def test_healthy_project(self, initialized_client: VaultItClient):
        result = initialized_client.doctor()
        assert result["healthy"] is True
        assert all(c["status"] != "fail" for c in result["checks"])

    def test_uninitialized_project(self, client: VaultItClient):
        result = client.doctor()
        assert result["healthy"] is False
        assert result["checks"][0]["status"] == "fail"


# ── diff ──


class TestDiff:
    def test_diff_between_versions(self, initialized_client: VaultItClient):
        initialized_client.sync(tasks=[])
        initialized_client.sync(
            tasks=[{"id": "TASK-0001", "title": "Added"}],
        )
        d = initialized_client.diff(from_version=1, to_version=2)
        assert d.from_version == 1
        assert d.to_version == 2
        assert len(d.tasks_added) == 1


# ── lifecycle ──


class TestFullLifecycle:
    def test_init_sync_bootstrap_status_doctor(self, tmp_path: Path):
        """Full end-to-end lifecycle test."""
        client = VaultItClient(project_dir=tmp_path)

        # Init
        config = client.init(name="Lifecycle Test")
        assert config.project_id == "lifecycle-test"

        # Sync 1
        h1 = client.sync(
            tasks=[{"id": "TASK-0001", "title": "Setup CI"}],
            decisions=[{"id": "DEC-0001", "summary": "Use GitHub Actions"}],
            open_questions=["Which Python versions to support?"],
            next_steps=["Configure pytest"],
            notes="Initial setup",
            agent="claude",
            agent_version="3.5-sonnet",
        )
        assert h1.version == 1

        # Sync 2
        h2 = client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "Setup CI", "status": "done"},
                {"id": "TASK-0002", "title": "Write docs"},
            ],
            next_steps=["Deploy to PyPI"],
            agent="claude",
        )
        assert h2.version == 2

        # Bootstrap
        briefing = client.bootstrap()
        assert "Lifecycle Test" in briefing
        assert "TASK-0001" in briefing
        assert "TASK-0002" in briefing

        # Status
        status = client.status()
        assert status["session_count"] == 1
        assert status["task_counts"]["done"] == 1
        assert status["task_counts"]["pending"] == 1

        # Diff
        diff = client.diff(1, 2)
        assert len(diff.tasks_added) == 1
        assert diff.tasks_added[0].id == "TASK-0002"
        assert len(diff.tasks_changed) == 1

        # Doctor
        doc = client.doctor()
        assert doc["healthy"] is True
