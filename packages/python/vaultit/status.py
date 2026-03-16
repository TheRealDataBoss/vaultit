"""vaultit status — show status of all projects in the bridge repo."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from git import Repo
from rich.console import Console
from rich.table import Table

console = Console()

STATUS_STYLES: dict[str, str] = {
    "EXECUTING": "bold yellow",
    "PROTOCOL_BREACH": "bold red",
    "IDLE": "dim",
    "VERIFIED": "green",
    "SEALED": "green",
    "AWAITING_REVIEW": "blue",
    "AWAITING_MANUAL_VALIDATION": "magenta",
    "PROPOSED": "cyan",
    "REVIEWED": "cyan",
    "VALIDATED": "green",
    "AWAITING_SEAL": "yellow",
}


def _load_config(cwd: Path) -> dict | None:
    config_path = cwd / ".vaultit"
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def show_status(bridge: str | None = None, json_output: bool = False) -> None:
    """Fetch and display status of all projects in the bridge repo."""
    cwd = Path.cwd()
    config = _load_config(cwd)
    bridge_repo = bridge or (config and config.get("bridge_repo"))

    console.print("\n  [cyan]vaultit status[/cyan]\n")

    if not bridge_repo:
        console.print("  [red]No bridge repo configured. Run vaultit init or pass --bridge.[/red]")
        raise SystemExit(1)

    tmp_dir = Path(tempfile.mkdtemp(prefix="vaultit-"))
    try:
        bridge_url = f"https://github.com/{bridge_repo}.git"

        with console.status("Fetching project states..."):
            Repo.clone_from(bridge_url, str(tmp_dir), depth=1)

        projects_dir = tmp_dir / "projects"
        if not projects_dir.exists():
            console.print("  [yellow]No projects directory found in bridge repo.[/yellow]")
            return

        project_dirs = sorted(
            [d for d in projects_dir.iterdir() if d.is_dir()]
        )

        if not project_dirs:
            console.print("  [yellow]No projects found.[/yellow]")
            return

        rows: list[dict[str, str]] = []
        for pdir in project_dirs:
            sv_path = pdir / "STATE_VECTOR.json"
            if not sv_path.exists():
                rows.append({
                    "name": pdir.name,
                    "type": "?",
                    "status": "NO STATE",
                    "task": "-",
                    "blocker": "-",
                    "updated": "-",
                })
                continue

            sv = json.loads(sv_path.read_text(encoding="utf-8"))
            task_id = sv.get("active_task_id")
            task_title = sv.get("active_task_title", "")
            task_str = f"{task_id}: {task_title}"[:50] if task_id else "-"

            blocker = sv.get("current_blocker")
            blocker_str = (blocker[:40] + "...") if blocker and len(blocker) > 40 else (blocker or "-")

            rows.append({
                "name": pdir.name,
                "type": sv.get("project_type", "?"),
                "status": sv.get("state_machine_status", "?"),
                "task": task_str,
                "blocker": blocker_str,
                "updated": sv.get("last_updated", "?"),
            })

        if json_output:
            console.print_json(json.dumps(rows, indent=2))
            return

        # Build rich table
        table = Table(show_header=True, header_style="bold", pad_edge=False, box=None)
        table.add_column("Project", style="white", min_width=16)
        table.add_column("Type", style="dim", min_width=14)
        table.add_column("Status", min_width=20)
        table.add_column("Active Task", style="white", min_width=30)
        table.add_column("Updated", style="dim", min_width=10)

        for row in rows:
            status_val = row["status"]
            style = STATUS_STYLES.get(status_val, "white")
            table.add_row(
                row["name"],
                row["type"],
                f"[{style}]{status_val}[/{style}]",
                row["task"],
                row["updated"],
            )

        console.print(table)

        # Show blockers
        blocked = [r for r in rows if r["blocker"] != "-"]
        if blocked:
            console.print("\n  [yellow]Blockers:[/yellow]")
            for row in blocked:
                console.print(f"    [red]{row['name']}:[/red] {row['blocker']}")

        console.print()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
