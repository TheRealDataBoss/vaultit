"""vaultit MCP server — expose tools via Model Context Protocol."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vaultit.client import VaultItClient

mcp = FastMCP(
    name="vaultit",
    instructions="Zero model drift between AI agents. Universal session continuity for Claude, GPT, Gemini, and any LLM.",
)


def _client() -> VaultItClient:
    return VaultItClient()


@mcp.tool()
def vaultit_init(
    name: str,
    backend: str = "file",
    coordination: str = "sequential",
) -> str:
    """Initialize a vaultit project in the current directory.

    Args:
        name: Project name
        backend: Storage backend - "file" or "sqlite"
        coordination: Coordination mode - "sequential", "lock", or "merge"
    """
    try:
        config = _client().init(name=name, backend_type=backend, coordination=coordination)
        return f"Initialized project '{config.name}' (id={config.project_id}, backend={config.backend})"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_sync(
    notes: str = "",
    agent: str = "custom",
    agent_version: str = "",
    next_steps: list[str] | None = None,
    open_questions: list[str] | None = None,
    tasks: list[dict] | None = None,
    decisions: list[dict] | None = None,
) -> str:
    """Sync current state — creates a versioned handoff.

    Args:
        notes: Free-form notes for this handoff
        agent: Agent type (claude, gpt, gemini, custom)
        agent_version: Agent version string
        next_steps: List of next steps
        open_questions: List of open questions
        tasks: List of task dicts with id, title, status
        decisions: List of decision dicts with id, summary
    """
    try:
        handoff = _client().sync(
            notes=notes,
            agent=agent,
            agent_version=agent_version,
            next_steps=next_steps,
            open_questions=open_questions,
            tasks=tasks,
            decisions=decisions,
        )
        return f"Synced handoff v{handoff.version} for session {handoff.session_id}"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_bootstrap() -> str:
    """Generate a bootstrap briefing from the latest handoff.

    Returns the full briefing text. This is the primary tool for session start.
    """
    try:
        return _client().bootstrap()
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_status() -> str:
    """Get project status summary.

    Returns project info, session count, latest handoff, and task counts.
    """
    try:
        result = _client().status()
        lines = [
            f"Project: {result['name']} ({result['project_id']})",
            f"Backend: {result['backend']}",
            f"Coordination: {result['coordination']}",
            f"Sessions: {result['session_count']}",
            f"Latest: {result['latest_handoff']}",
        ]
        if result["task_counts"]:
            counts = ", ".join(f"{k}: {v}" for k, v in result["task_counts"].items())
            lines.append(f"Tasks: {counts}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_doctor() -> str:
    """Run health checks on the vaultit project.

    Returns check results for directory, config, backend, handoffs, and lock.
    """
    try:
        result = _client().doctor()
        lines = []
        for check in result["checks"]:
            icon = {"ok": "PASS", "fail": "FAIL", "warn": "WARN", "info": "INFO"}.get(check["status"], "?")
            lines.append(f"[{icon}] {check['name']}: {check['message']}")
        status = "HEALTHY" if result["healthy"] else "UNHEALTHY"
        lines.append(f"\nOverall: {status}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_add_task(
    task_id: str,
    title: str,
    status: str = "pending",
    owner: str = "human",
    notes: str = "",
) -> str:
    """Add or update a task in the latest handoff. Creates a new handoff version.

    Args:
        task_id: Task ID in format TASK-XXXX
        title: Task title
        status: Task status (pending, in_progress, done, blocked)
        owner: Task owner
        notes: Optional notes
    """
    try:
        handoff = _client().add_task(
            task_id=task_id, title=title, status=status, owner=owner, notes=notes,
        )
        return f"Task {task_id} saved. Handoff v{handoff.version} ({len(handoff.tasks)} tasks total)"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_update_task(task_id: str, status: str) -> str:
    """Update the status of an existing task. Creates a new handoff version.

    Args:
        task_id: Task ID to update (e.g. TASK-0001)
        status: New status (pending, in_progress, done, blocked)
    """
    try:
        handoff = _client().update_task_status(task_id, status)
        return f"Task {task_id} updated to '{status}'. Handoff v{handoff.version}"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_add_decision(
    decision_id: str,
    summary: str,
    rationale: str = "",
    made_by: str = "human",
) -> str:
    """Add a decision to the latest handoff. Creates a new handoff version.

    Args:
        decision_id: Decision ID in format DEC-XXXX
        summary: Decision summary
        rationale: Rationale for the decision
        made_by: Who made the decision
    """
    try:
        handoff = _client().add_decision(
            decision_id=decision_id, summary=summary, rationale=rationale, made_by=made_by,
        )
        return f"Decision {decision_id} recorded. Handoff v{handoff.version} ({len(handoff.decisions)} decisions total)"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_list_sessions() -> str:
    """List all sessions for the current project."""
    try:
        sessions = _client().list_sessions()
        if not sessions:
            return "No sessions found."
        lines = []
        for s in sessions:
            closed = s.closed_at.isoformat() if s.closed_at else "open"
            lines.append(f"{s.id[:12]}  agent={s.agent.value}  created={s.created_at.isoformat()}  status={closed}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def vaultit_diff(from_version: int, to_version: int) -> str:
    """Compare two handoff versions and show what changed.

    Args:
        from_version: Starting version number
        to_version: Ending version number
    """
    try:
        d = _client().diff(from_version, to_version)
        lines = [f"Diff: v{d.from_version} -> v{d.to_version}"]
        if d.tasks_added:
            lines.append(f"  Tasks added: {', '.join(t.id for t in d.tasks_added)}")
        if d.tasks_removed:
            lines.append(f"  Tasks removed: {', '.join(t.id for t in d.tasks_removed)}")
        if d.tasks_changed:
            lines.append(f"  Tasks changed: {', '.join(t.id for t in d.tasks_changed)}")
        if d.decisions_added:
            lines.append(f"  Decisions added: {', '.join(d2.id for d2 in d.decisions_added)}")
        if d.questions_added:
            lines.append(f"  Questions added: {len(d.questions_added)}")
        if d.next_steps_changed:
            lines.append(f"  Next steps changed: {len(d.next_steps_changed)}")
        if len(lines) == 1:
            lines.append("  No changes detected.")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"


def main():
    """Entry point for vaultit-mcp command."""
    mcp.run()


if __name__ == "__main__":
    main()
