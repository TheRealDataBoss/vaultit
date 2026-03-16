"""Bootstrap prompt renderer for vaultit."""

from __future__ import annotations

from vaultit.models import Handoff, ProjectConfig, TaskStatus


def render_bootstrap(handoff: Handoff, config: ProjectConfig) -> str:
    """Render a structured plain-text briefing from a handoff and config.

    Designed to be pasted into any AI chat as a project context bootstrap.
    """
    lines: list[str] = []

    # ── PROJECT ──
    lines.append("=" * 60)
    lines.append("PROJECT BOOTSTRAP BRIEFING")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Project: {config.name} ({config.project_id})")
    lines.append(f"Schema:  {config.schema_version}")
    lines.append(f"Mode:    {config.coordination}")
    lines.append("")

    # ── SESSION ──
    lines.append("-" * 40)
    lines.append("SESSION")
    lines.append("-" * 40)
    lines.append(f"Session ID:    {handoff.session_id}")
    lines.append(f"Handoff ID:    {handoff.id}")
    lines.append(f"Version:       {handoff.version}")
    lines.append(f"Agent:         {handoff.agent.value}")
    if handoff.agent_version:
        lines.append(f"Agent Version: {handoff.agent_version}")
    lines.append(f"Created:       {handoff.created_at.isoformat()}")
    lines.append(f"Updated:       {handoff.updated_at.isoformat()}")
    lines.append("")

    # ── TASKS ──
    if handoff.tasks:
        lines.append("-" * 40)
        lines.append("TASKS")
        lines.append("-" * 40)
        for status in TaskStatus:
            group = [t for t in handoff.tasks if t.status == status]
            if not group:
                continue
            lines.append(f"  [{status.value.upper()}]")
            for t in group:
                deps = f" (depends: {', '.join(t.depends_on)})" if t.depends_on else ""
                lines.append(f"    {t.id}: {t.title} [owner: {t.owner}]{deps}")
                if t.notes:
                    lines.append(f"           note: {t.notes}")
        lines.append("")

    # ── DECISIONS ──
    if handoff.decisions:
        lines.append("-" * 40)
        lines.append("DECISIONS")
        lines.append("-" * 40)
        for d in handoff.decisions:
            lines.append(f"  {d.id}: {d.summary}")
            if d.rationale:
                lines.append(f"         rationale: {d.rationale}")
            if d.supersedes:
                lines.append(f"         supersedes: {d.supersedes}")
        lines.append("")

    # ── OPEN QUESTIONS ──
    if handoff.open_questions:
        lines.append("-" * 40)
        lines.append("OPEN QUESTIONS")
        lines.append("-" * 40)
        for i, q in enumerate(handoff.open_questions, 1):
            lines.append(f"  {i}. {q}")
        lines.append("")

    # ── NEXT STEPS ──
    if handoff.next_steps:
        lines.append("-" * 40)
        lines.append("NEXT STEPS")
        lines.append("-" * 40)
        for i, s in enumerate(handoff.next_steps, 1):
            lines.append(f"  {i}. {s}")
        lines.append("")

    # ── NOTES ──
    if handoff.raw_notes:
        lines.append("-" * 40)
        lines.append("NOTES")
        lines.append("-" * 40)
        lines.append(handoff.raw_notes)
        lines.append("")

    lines.append("=" * 60)
    lines.append("END BRIEFING")
    lines.append("=" * 60)

    return "\n".join(lines)
