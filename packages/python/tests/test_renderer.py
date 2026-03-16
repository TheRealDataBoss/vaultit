"""Tests for bootstrap renderer output."""

from vaultit.models import (
    AgentType,
    Decision,
    Handoff,
    ProjectConfig,
    Task,
    TaskStatus,
)
from vaultit.renderer import render_bootstrap


def _make_config(**kwargs) -> ProjectConfig:
    defaults = {"project_id": "test-proj", "name": "Test Project"}
    defaults.update(kwargs)
    return ProjectConfig(**defaults)


def _make_handoff(**kwargs) -> Handoff:
    defaults = {"session_id": "sess-001", "project_id": "test-proj"}
    defaults.update(kwargs)
    return Handoff(**defaults)


class TestRenderBootstrap:
    def test_contains_header(self):
        output = render_bootstrap(_make_handoff(), _make_config())
        assert "PROJECT BOOTSTRAP BRIEFING" in output
        assert "END BRIEFING" in output

    def test_contains_project_info(self):
        output = render_bootstrap(_make_handoff(), _make_config(name="My App"))
        assert "My App" in output
        assert "test-proj" in output

    def test_contains_session_info(self):
        output = render_bootstrap(
            _make_handoff(agent=AgentType.claude, agent_version="3.5"),
            _make_config(),
        )
        assert "SESSION" in output
        assert "claude" in output
        assert "3.5" in output

    def test_contains_tasks_grouped_by_status(self):
        tasks = [
            Task(id="TASK-0001", title="Pending task", status=TaskStatus.pending),
            Task(id="TASK-0002", title="Done task", status=TaskStatus.done),
            Task(id="TASK-0003", title="Blocked task", status=TaskStatus.blocked),
        ]
        output = render_bootstrap(_make_handoff(tasks=tasks), _make_config())
        assert "TASKS" in output
        assert "PENDING" in output
        assert "DONE" in output
        assert "BLOCKED" in output
        assert "TASK-0001" in output
        assert "TASK-0002" in output
        assert "TASK-0003" in output

    def test_contains_decisions(self):
        decisions = [
            Decision(id="DEC-0001", summary="Use Pydantic", rationale="Type safety"),
        ]
        output = render_bootstrap(_make_handoff(decisions=decisions), _make_config())
        assert "DECISIONS" in output
        assert "DEC-0001" in output
        assert "Use Pydantic" in output
        assert "Type safety" in output

    def test_contains_open_questions(self):
        output = render_bootstrap(
            _make_handoff(open_questions=["Should we use SQLite?"]),
            _make_config(),
        )
        assert "OPEN QUESTIONS" in output
        assert "Should we use SQLite?" in output

    def test_contains_next_steps(self):
        output = render_bootstrap(
            _make_handoff(next_steps=["Deploy", "Write docs"]),
            _make_config(),
        )
        assert "NEXT STEPS" in output
        assert "Deploy" in output
        assert "Write docs" in output

    def test_contains_notes(self):
        output = render_bootstrap(
            _make_handoff(raw_notes="Important context here"),
            _make_config(),
        )
        assert "NOTES" in output
        assert "Important context here" in output

    def test_omits_empty_sections(self):
        output = render_bootstrap(_make_handoff(), _make_config())
        assert "TASKS" not in output
        assert "DECISIONS" not in output
        assert "OPEN QUESTIONS" not in output
        assert "NEXT STEPS" not in output
        assert "NOTES" not in output

    def test_task_dependencies_shown(self):
        tasks = [
            Task(
                id="TASK-0002",
                title="Deploy",
                depends_on=["TASK-0001"],
            ),
        ]
        output = render_bootstrap(_make_handoff(tasks=tasks), _make_config())
        assert "depends: TASK-0001" in output

    def test_decision_supersedes_shown(self):
        decisions = [
            Decision(id="DEC-0002", summary="Switch DB", supersedes="DEC-0001"),
        ]
        output = render_bootstrap(_make_handoff(decisions=decisions), _make_config())
        assert "supersedes: DEC-0001" in output
