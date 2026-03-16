"""CLI entry point for vaultit — thin wrapper over VaultItClient."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vaultit.client import VaultItClient
from vaultit.exceptions import VaultItError

app = typer.Typer(
    name="vaultit",
    help="Zero model drift between AI agents.",
    add_completion=False,
    no_args_is_help=True,
)

sessions_app = typer.Typer(help="Manage sessions.", no_args_is_help=True)
tasks_app = typer.Typer(help="Manage tasks.", no_args_is_help=True)
decisions_app = typer.Typer(help="Manage decisions.", no_args_is_help=True)
auth_app = typer.Typer(help="Manage API keys.", no_args_is_help=True)

app.add_typer(sessions_app, name="sessions")
app.add_typer(tasks_app, name="tasks")
app.add_typer(decisions_app, name="decisions")
app.add_typer(auth_app, name="auth")

console = Console()
err_console = Console(stderr=True)


def _get_client() -> VaultItClient:
    return VaultItClient(project_dir=Path("."))


def _handle_error(exc: Exception) -> None:
    err_console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=1)


# ── top-level commands ──


@app.command()
def init(
    name: str = typer.Option(..., "--name", "-n", help="Project name"),
    coordination: str = typer.Option(
        "sequential", "--coordination", "-c",
        help="Coordination mode: sequential, lock, or merge",
    ),
    backend: str = typer.Option(
        "file", "--backend", "-b", help="Backend: file, sqlite, or postgres",
    ),
) -> None:
    """Initialize a new vaultit project in the current directory."""
    try:
        client = _get_client()
        config = client.init(name=name, coordination=coordination, backend_type=backend)
        console.print(Panel(
            f"[green]Initialized project[/green] [bold]{config.name}[/bold]\n"
            f"  ID:           {config.project_id}\n"
            f"  Backend:      {config.backend}\n"
            f"  Coordination: {config.coordination}\n"
            f"  Schema:       {config.schema_version}",
            title="vaultit init",
            border_style="green",
        ))
    except VaultItError as exc:
        _handle_error(exc)


def _parse_task(raw: str) -> dict:
    parts = raw.split(":", 2)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        err_console.print(
            f"[red]Error:[/red] Malformed --task: '{raw}'\n"
            "  Expected format: TASK-XXXX:title or TASK-XXXX:title:status"
        )
        raise typer.Exit(code=1)
    result: dict = {"id": parts[0].strip(), "title": parts[1].strip()}
    if len(parts) == 3 and parts[2].strip():
        result["status"] = parts[2].strip()
    return result


@app.command()
def sync(
    notes: str = typer.Option("", "--notes", help="Free-form notes for this handoff"),
    agent: str = typer.Option("custom", "--agent", help="Agent type: claude, gpt, gemini, custom"),
    agent_version: str = typer.Option("", "--agent-version", help="Agent version string"),
    next_step: Optional[list[str]] = typer.Option(None, "--next-step", help="Add a next step (repeatable)"),
    question: Optional[list[str]] = typer.Option(None, "--question", help="Add an open question (repeatable)"),
    task: Optional[list[str]] = typer.Option(None, "--task", help="Add a task as TASK-XXXX:title[:status] (repeatable)"),
) -> None:
    """Sync current state -- creates a versioned handoff."""
    try:
        tasks_parsed = [_parse_task(t) for t in (task or [])]
        client = _get_client()
        handoff = client.sync(
            notes=notes, agent=agent, agent_version=agent_version,
            next_steps=next_step or None,
            open_questions=question or None,
            tasks=tasks_parsed or None,
        )
        console.print(Panel(
            f"[green]Handoff synced[/green]\n"
            f"  Session: {handoff.session_id}\n"
            f"  Version: {handoff.version}\n"
            f"  Agent:   {handoff.agent.value}\n"
            f"  Tasks:   {len(handoff.tasks)}\n"
            f"  Steps:   {len(handoff.next_steps)}\n"
            f"  Q's:     {len(handoff.open_questions)}",
            title="vaultit sync",
            border_style="green",
        ))
    except VaultItError as exc:
        _handle_error(exc)


@app.command()
def bootstrap() -> None:
    """Generate a bootstrap briefing from the latest handoff."""
    try:
        client = _get_client()
        console.print(client.bootstrap())
    except VaultItError as exc:
        _handle_error(exc)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show project status summary."""
    try:
        client = _get_client()
        result = client.status()
        if json_output:
            console.print(json.dumps(result, indent=2))
            return
        table = Table(title="vaultit status", border_style="cyan")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Project", f"{result['name']} ({result['project_id']})")
        table.add_row("Backend", result["backend"])
        table.add_row("Coordination", result["coordination"])
        table.add_row("Sessions", str(result["session_count"]))
        table.add_row("Latest Handoff", result["latest_handoff"])
        if result["task_counts"]:
            counts = ", ".join(f"{k}: {v}" for k, v in result["task_counts"].items())
            table.add_row("Tasks", counts)
        console.print(table)
    except VaultItError as exc:
        _handle_error(exc)


@app.command()
def doctor() -> None:
    """Run health checks on the vaultit project."""
    try:
        client = _get_client()
        result = client.doctor()
        status_icons = {
            "ok": "[green]OK[/green]",
            "fail": "[red]FAIL[/red]",
            "warn": "[yellow]WARN[/yellow]",
            "info": "[cyan]INFO[/cyan]",
        }
        table = Table(title="vaultit doctor", border_style="cyan")
        table.add_column("Check", style="bold")
        table.add_column("Status")
        table.add_column("Detail")
        for check in result["checks"]:
            icon = status_icons.get(check["status"], "?")
            table.add_row(check["name"], icon, check["message"])
        console.print(table)
        if result["healthy"]:
            console.print("\n[green bold]All checks passed.[/green bold]")
        else:
            console.print("\n[red bold]Some checks failed.[/red bold]")
            raise typer.Exit(code=1)
    except VaultItError as exc:
        _handle_error(exc)


@app.command()
def migrate(
    to: str = typer.Option(..., "--to", help="Target backend: file, sqlite, or postgres"),
) -> None:
    """Migrate data from current backend to a different backend."""
    try:
        client = _get_client()
        result = client.switch_backend(to)
        console.print(Panel(
            f"[green]Migration complete[/green]\n"
            f"  From:     {result['from']}\n"
            f"  To:       {result['to']}\n"
            f"  Sessions: {result['sessions']}\n"
            f"  Handoffs: {result['handoffs']}",
            title="vaultit migrate",
            border_style="green",
        ))
    except VaultItError as exc:
        _handle_error(exc)


@app.command(name="export")
def export_cmd(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write briefing to file"),
) -> None:
    """Export bootstrap briefing to stdout or file."""
    try:
        client = _get_client()
        out_path = Path(output) if output else None
        briefing = client.export_briefing(output_path=out_path)
        if out_path:
            console.print(f"[green]Exported to {out_path}[/green]")
        else:
            console.print(briefing)
    except VaultItError as exc:
        _handle_error(exc)


@app.command(name="diff")
def diff_cmd(
    from_version: int = typer.Argument(..., help="Starting version"),
    to_version: int = typer.Argument(..., help="Ending version"),
) -> None:
    """Show diff between two handoff versions."""
    try:
        client = _get_client()
        d = client.diff(from_version, to_version)
        table = Table(title=f"Diff v{d.from_version} -> v{d.to_version}", border_style="cyan")
        table.add_column("Change", style="bold")
        table.add_column("Detail")
        if d.tasks_added:
            for t in d.tasks_added:
                table.add_row("[green]+ Task[/green]", f"{t.id}: {t.title}")
        if d.tasks_removed:
            for t in d.tasks_removed:
                table.add_row("[red]- Task[/red]", f"{t.id}: {t.title}")
        if d.tasks_changed:
            for t in d.tasks_changed:
                table.add_row("[yellow]~ Task[/yellow]", f"{t.id}: {t.title} [{t.status.value}]")
        if d.decisions_added:
            for dec in d.decisions_added:
                table.add_row("[green]+ Decision[/green]", f"{dec.id}: {dec.summary}")
        if d.questions_added:
            for q in d.questions_added:
                table.add_row("[green]+ Question[/green]", q)
        if d.next_steps_changed:
            for s in d.next_steps_changed:
                table.add_row("[yellow]~ Step[/yellow]", s)
        if not any([d.tasks_added, d.tasks_removed, d.tasks_changed,
                     d.decisions_added, d.questions_added, d.next_steps_changed]):
            table.add_row("(none)", "No changes detected")
        console.print(table)
    except VaultItError as exc:
        _handle_error(exc)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", help="Port to bind"),
) -> None:
    """Start the REST API server."""
    try:
        import uvicorn
        uvicorn.run("vaultit.server:app", host=host, port=port)
    except ImportError:
        err_console.print("[red]Error:[/red] uvicorn not installed. Run: pip install vaultit[server]")
        raise typer.Exit(code=1)


# ── sessions subcommands ──


@sessions_app.command(name="list")
def sessions_list() -> None:
    """List all sessions."""
    try:
        client = _get_client()
        sessions = client.list_sessions()
        if not sessions:
            console.print("No sessions found.")
            return
        table = Table(title="Sessions", border_style="cyan")
        table.add_column("ID", style="bold")
        table.add_column("Agent")
        table.add_column("Created")
        table.add_column("Status")
        for s in sessions:
            status_str = "open" if s.closed_at is None else f"closed {s.closed_at.isoformat()}"
            table.add_row(
                s.id[:12],
                s.agent.value,
                s.created_at.isoformat()[:19],
                status_str,
            )
        console.print(table)
    except VaultItError as exc:
        _handle_error(exc)


@sessions_app.command(name="open")
def sessions_open(
    agent: str = typer.Option("custom", "--agent", help="Agent type"),
    agent_version: str = typer.Option("", "--agent-version", help="Agent version"),
) -> None:
    """Open a new session."""
    try:
        client = _get_client()
        session = client.open_session(agent=agent, agent_version=agent_version)
        console.print(Panel(
            f"[green]Session opened[/green]\n  ID: {session.id}\n  Agent: {session.agent.value}",
            title="vaultit sessions open",
            border_style="green",
        ))
    except VaultItError as exc:
        _handle_error(exc)


@sessions_app.command(name="close")
def sessions_close(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to close (default: current)"),
) -> None:
    """Close a session."""
    try:
        client = _get_client()
        session = client.close_session(session_id)
        console.print(f"[green]Closed session {session.id[:12]}[/green]")
    except VaultItError as exc:
        _handle_error(exc)


# ── tasks subcommands ──


@tasks_app.command(name="add")
def tasks_add(
    task_id: str = typer.Argument(..., help="Task ID (e.g. TASK-0001)"),
    title: str = typer.Argument(..., help="Task title"),
    status_opt: str = typer.Option("pending", "--status", "-s", help="Task status"),
    owner: str = typer.Option("human", "--owner", help="Task owner"),
) -> None:
    """Add or update a task."""
    try:
        client = _get_client()
        handoff = client.add_task(task_id=task_id, title=title, status=status_opt, owner=owner)
        console.print(Panel(
            f"[green]Task {task_id} saved[/green]\n"
            f"  Title:   {title}\n"
            f"  Status:  {status_opt}\n"
            f"  Handoff: v{handoff.version} ({len(handoff.tasks)} tasks)",
            title="vaultit tasks add",
            border_style="green",
        ))
    except (VaultItError, ValueError) as exc:
        _handle_error(exc)


@tasks_app.command(name="update")
def tasks_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    status_val: str = typer.Argument(..., help="New status: pending, in_progress, done, blocked"),
) -> None:
    """Update task status."""
    try:
        client = _get_client()
        handoff = client.update_task_status(task_id, status_val)
        console.print(f"[green]Task {task_id} -> {status_val} (handoff v{handoff.version})[/green]")
    except (VaultItError, ValueError) as exc:
        _handle_error(exc)


# ── decisions subcommands ──


@decisions_app.command(name="add")
def decisions_add(
    decision_id: str = typer.Argument(..., help="Decision ID (e.g. DEC-0001)"),
    summary: str = typer.Argument(..., help="Decision summary"),
    rationale: str = typer.Option("", "--rationale", "-r", help="Rationale"),
    made_by: str = typer.Option("human", "--made-by", help="Who made the decision"),
) -> None:
    """Add a decision."""
    try:
        client = _get_client()
        handoff = client.add_decision(
            decision_id=decision_id, summary=summary,
            rationale=rationale, made_by=made_by,
        )
        console.print(Panel(
            f"[green]Decision {decision_id} recorded[/green]\n"
            f"  Summary:   {summary}\n"
            f"  Rationale: {rationale or '(none)'}\n"
            f"  Handoff:   v{handoff.version} ({len(handoff.decisions)} decisions)",
            title="vaultit decisions add",
            border_style="green",
        ))
    except (VaultItError, ValueError) as exc:
        _handle_error(exc)


# ── auth subcommands ──


@auth_app.command(name="keygen")
def auth_keygen(
    name: str = typer.Option(..., "--name", help="Key name"),
    scopes: Optional[list[str]] = typer.Option(None, "--scopes", help="Scopes (repeatable): read, write, admin"),
    expires_days: Optional[int] = typer.Option(None, "--expires-days", help="Expire key after N days"),
) -> None:
    """Generate a new API key."""
    try:
        from vaultit.auth import APIKeyManager
        mgr = APIKeyManager()
        plaintext, api_key = mgr.generate_key(
            name=name,
            user_id="cli-user",
            scopes=scopes or ["read", "write"],
            expires_in_days=expires_days,
        )
        console.print(Panel(
            f"[green]API key generated[/green]\n"
            f"  Name:    {api_key.name}\n"
            f"  ID:      {api_key.id}\n"
            f"  Scopes:  {', '.join(api_key.scopes)}\n"
            f"  Expires: {api_key.expires_at or 'never'}\n\n"
            f"  [bold yellow]Key: {plaintext}[/bold yellow]\n\n"
            f"  [red]Save this key now -- it will not be shown again.[/red]",
            title="vaultit auth keygen",
            border_style="green",
        ))
    except Exception as exc:
        _handle_error(exc)


@auth_app.command(name="keys")
def auth_keys() -> None:
    """List all API keys (hash redacted)."""
    try:
        from vaultit.auth import APIKeyManager
        mgr = APIKeyManager()
        keys = mgr.list_keys()
        if not keys:
            console.print("No API keys found.")
            return
        table = Table(title="API Keys", border_style="cyan")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Scopes")
        table.add_column("Created")
        table.add_column("Last Used")
        for k in keys:
            table.add_row(
                k.id,
                k.name,
                ", ".join(k.scopes),
                k.created_at.isoformat()[:19],
                k.last_used_at.isoformat()[:19] if k.last_used_at else "never",
            )
        console.print(table)
    except Exception as exc:
        _handle_error(exc)


@auth_app.command(name="revoke")
def auth_revoke(
    key_id: str = typer.Argument(..., help="API key ID to revoke"),
) -> None:
    """Revoke an API key."""
    try:
        from vaultit.auth import APIKeyManager
        mgr = APIKeyManager()
        if mgr.revoke_key(key_id):
            console.print(f"[green]Revoked key {key_id}[/green]")
        else:
            console.print(f"[red]Key {key_id} not found[/red]")
            raise typer.Exit(code=1)
    except Exception as exc:
        _handle_error(exc)


if __name__ == "__main__":
    app()
