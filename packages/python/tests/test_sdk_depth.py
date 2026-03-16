"""Tests for Phase 3 SDK depth — session, handoff, task, decision, export methods."""

from pathlib import Path

import pytest

from vaultit.client import VaultItClient
from vaultit.exceptions import VaultItError, HandoffNotFoundError
from vaultit.models import AgentType, TaskStatus


@pytest.fixture
def client(tmp_path: Path) -> VaultItClient:
    c = VaultItClient(project_dir=tmp_path)
    c.init(name="SDK Test")
    return c


@pytest.fixture
def client_with_handoff(client: VaultItClient) -> VaultItClient:
    client.sync(
        notes="seed",
        tasks=[{"id": "TASK-0001", "title": "Alpha"}, {"id": "TASK-0002", "title": "Beta"}],
        decisions=[{"id": "DEC-0001", "summary": "Use file backend"}],
        next_steps=["Step one"],
        open_questions=["Why?"],
    )
    return client


# ── session management ──


class TestSessionManagement:
    def test_open_session(self, client: VaultItClient):
        session = client.open_session(agent="claude")
        assert session.agent == AgentType.claude
        assert session.closed_at is None

    def test_open_multiple_sessions(self, client: VaultItClient):
        s1 = client.open_session()
        s2 = client.open_session()
        assert s1.id != s2.id
        sessions = client.list_sessions()
        assert len(sessions) >= 2

    def test_close_session_by_id(self, client: VaultItClient):
        session = client.open_session()
        closed = client.close_session(session.id)
        assert closed.closed_at is not None
        assert closed.id == session.id

    def test_close_current_session(self, client: VaultItClient):
        session = client.open_session()
        closed = client.close_session()
        assert closed.closed_at is not None
        assert closed.id == session.id

    def test_close_no_open_session_raises(self, client: VaultItClient):
        s = client.open_session()
        client.close_session(s.id)
        with pytest.raises(VaultItError, match="No open sessions"):
            client.close_session()

    def test_get_session(self, client: VaultItClient):
        session = client.open_session(agent="gpt")
        fetched = client.get_session(session.id)
        assert fetched.id == session.id
        assert fetched.agent == AgentType.gpt

    def test_list_sessions_newest_first(self, client: VaultItClient):
        s1 = client.open_session()
        s2 = client.open_session()
        sessions = client.list_sessions()
        assert sessions[0].id == s2.id
        assert sessions[1].id == s1.id

    def test_list_sessions_empty(self, client: VaultItClient):
        sessions = client.list_sessions()
        assert sessions == []


# ── handoff management ──


class TestHandoffManagement:
    def test_get_handoff(self, client_with_handoff: VaultItClient):
        sessions = client_with_handoff.list_sessions()
        session_id = sessions[0].id
        handoff = client_with_handoff.get_handoff(session_id, 1)
        assert handoff.version == 1
        assert handoff.raw_notes == "seed"

    def test_list_handoffs_newest_first(self, client_with_handoff: VaultItClient):
        # Create a second handoff in the same session
        client_with_handoff.sync(notes="second")
        sessions = client_with_handoff.list_sessions()
        session_id = sessions[0].id
        handoffs = client_with_handoff.list_handoffs(session_id)
        assert len(handoffs) == 2
        assert handoffs[0].version == 2
        assert handoffs[1].version == 1

    def test_get_handoff_wrong_version_raises(self, client_with_handoff: VaultItClient):
        sessions = client_with_handoff.list_sessions()
        session_id = sessions[0].id
        with pytest.raises(Exception):
            client_with_handoff.get_handoff(session_id, 999)

    def test_list_handoffs_no_handoffs(self, client: VaultItClient):
        s = client.open_session()
        handoffs = client.list_handoffs(s.id)
        assert handoffs == []


# ── task management ──


class TestTaskManagement:
    def test_add_task(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.add_task(
            task_id="TASK-0003", title="Gamma", status="in_progress",
        )
        assert len(handoff.tasks) == 3
        added = [t for t in handoff.tasks if t.id == "TASK-0003"][0]
        assert added.title == "Gamma"
        assert added.status == TaskStatus.in_progress

    def test_add_task_upserts_existing(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.add_task(
            task_id="TASK-0001", title="Alpha Updated", status="done",
        )
        assert len(handoff.tasks) == 2  # still 2, not 3
        updated = [t for t in handoff.tasks if t.id == "TASK-0001"][0]
        assert updated.title == "Alpha Updated"
        assert updated.status == TaskStatus.done

    def test_update_task_status(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.update_task_status("TASK-0001", "done")
        task = [t for t in handoff.tasks if t.id == "TASK-0001"][0]
        assert task.status == TaskStatus.done

    def test_update_task_status_not_found(self, client_with_handoff: VaultItClient):
        with pytest.raises(ValueError, match="TASK-9999"):
            client_with_handoff.update_task_status("TASK-9999", "done")

    def test_add_task_no_handoff_raises(self, client: VaultItClient):
        with pytest.raises(HandoffNotFoundError):
            client.add_task(task_id="TASK-0001", title="No handoff yet")

    def test_add_task_with_owner_and_notes(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.add_task(
            task_id="TASK-0004", title="Delta",
            owner="agent", notes="Important task",
        )
        added = [t for t in handoff.tasks if t.id == "TASK-0004"][0]
        assert added.owner == "agent"
        assert added.notes == "Important task"

    def test_task_creates_new_version(self, client_with_handoff: VaultItClient):
        h1 = client_with_handoff.add_task(task_id="TASK-0003", title="Gamma")
        h2 = client_with_handoff.add_task(task_id="TASK-0004", title="Delta")
        assert h2.version == h1.version + 1


# ── decision management ──


class TestDecisionManagement:
    def test_add_decision(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.add_decision(
            decision_id="DEC-0002", summary="Switch to sqlite",
            rationale="Better concurrency",
        )
        assert len(handoff.decisions) == 2
        added = [d for d in handoff.decisions if d.id == "DEC-0002"][0]
        assert added.summary == "Switch to sqlite"
        assert added.rationale == "Better concurrency"

    def test_add_decision_no_handoff_raises(self, client: VaultItClient):
        with pytest.raises(HandoffNotFoundError):
            client.add_decision(decision_id="DEC-0001", summary="Nope")

    def test_add_decision_with_supersedes(self, client_with_handoff: VaultItClient):
        handoff = client_with_handoff.add_decision(
            decision_id="DEC-0002", summary="Override",
            supersedes="DEC-0001",
        )
        added = [d for d in handoff.decisions if d.id == "DEC-0002"][0]
        assert added.supersedes == "DEC-0001"

    def test_decision_creates_new_version(self, client_with_handoff: VaultItClient):
        h1 = client_with_handoff.add_decision(
            decision_id="DEC-0002", summary="First",
        )
        h2 = client_with_handoff.add_decision(
            decision_id="DEC-0003", summary="Second",
        )
        assert h2.version == h1.version + 1


# ── export ──


class TestExport:
    def test_export_returns_briefing(self, client_with_handoff: VaultItClient):
        briefing = client_with_handoff.export_briefing()
        assert "SDK Test" in briefing or "sdk-test" in briefing

    def test_export_to_file(self, client_with_handoff: VaultItClient, tmp_path: Path):
        out = tmp_path / "briefing.md"
        briefing = client_with_handoff.export_briefing(output_path=out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content == briefing

    def test_export_no_handoff(self, client: VaultItClient):
        briefing = client.export_briefing()
        assert "no handoffs" in briefing.lower() or "sync" in briefing.lower()

    def test_export_to_file_no_handoff(self, client: VaultItClient, tmp_path: Path):
        out = tmp_path / "empty.md"
        briefing = client.export_briefing(output_path=out)
        assert out.exists()
        assert briefing == out.read_text(encoding="utf-8")
