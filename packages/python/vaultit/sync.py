"""vaultit sync — push state files to the bridge repo."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
from git import Repo
from rich.console import Console
from rich.spinner import Spinner

console = Console()


def _load_config(cwd: Path) -> dict | None:
    config_path = cwd / ".vaultit"
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def _load_schema() -> dict | None:
    # Try relative to this package (installed from repo)
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "protocol" / "vaultit.schema.json",
        Path.home() / ".vaultit" / "src" / "protocol" / "vaultit.schema.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def sync_project(bridge: str | None = None, dry_run: bool = False) -> None:
    """Sync state files to the vaultit bridge repo."""
    cwd = Path.cwd()
    config = _load_config(cwd)

    console.print("\n  [cyan]vaultit sync[/cyan]\n")

    if not config and not bridge:
        console.print("  [red]No .vaultit config found. Run vaultit init first, or pass --bridge.[/red]")
        raise SystemExit(1)

    bridge_repo = bridge or (config and config.get("bridge_repo"))
    project_name = config.get("project_name", "") if config else ""
    sv_rel = config.get("state_vector_path", "handoff/STATE_VECTOR.json") if config else "handoff/STATE_VECTOR.json"
    handoff_rel = config.get("handoff_path", "docs/HANDOFF.md") if config else "docs/HANDOFF.md"

    if not bridge_repo:
        console.print("  [red]No bridge repo configured. Run vaultit init or pass --bridge.[/red]")
        raise SystemExit(1)

    if not project_name:
        console.print("  [red]No project_name in .vaultit config.[/red]")
        raise SystemExit(1)

    # Read and validate STATE_VECTOR.json
    sv_path = cwd / sv_rel
    if not sv_path.exists():
        console.print(f"  [red]STATE_VECTOR.json not found at {sv_path}[/red]")
        raise SystemExit(1)

    with console.status("Validating STATE_VECTOR.json..."):
        state_vector = json.loads(sv_path.read_text(encoding="utf-8"))
        schema = _load_schema()
        if schema:
            try:
                jsonschema.validate(instance=state_vector, schema=schema)
            except jsonschema.ValidationError as e:
                console.print(f"  [red]Validation failed: {e.message}[/red]")
                raise SystemExit(1)

    console.print("  [green]STATE_VECTOR.json is valid[/green]")

    if dry_run:
        console.print("\n  [yellow]Dry run -- would sync:[/yellow]")
        console.print(f"    {sv_rel} -> projects/{project_name}/STATE_VECTOR.json")
        handoff_path = cwd / handoff_rel
        if handoff_path.exists():
            console.print(f"    {handoff_rel} -> projects/{project_name}/HANDOFF.md")
        console.print()
        return

    # Clone bridge repo, copy files, commit, push
    tmp_dir = Path(tempfile.mkdtemp(prefix="vaultit-"))
    try:
        bridge_url = f"https://github.com/{bridge_repo}.git"

        with console.status("Cloning bridge repo..."):
            repo = Repo.clone_from(bridge_url, str(tmp_dir), depth=1)

        console.print("  [green]Bridge repo cloned[/green]")

        target_dir = tmp_dir / "projects" / project_name
        target_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(sv_path), str(target_dir / "STATE_VECTOR.json"))
        console.print("  [green]Copied: STATE_VECTOR.json[/green]")

        handoff_path = cwd / handoff_rel
        if handoff_path.exists():
            shutil.copy2(str(handoff_path), str(target_dir / "HANDOFF.md"))
            console.print("  [green]Copied: HANDOFF.md[/green]")

        next_task_path = cwd / "docs" / "NEXT_TASK.md"
        if next_task_path.exists():
            shutil.copy2(str(next_task_path), str(target_dir / "NEXT_TASK.md"))
            console.print("  [green]Copied: NEXT_TASK.md[/green]")

        # Commit and push
        with console.status("Pushing to bridge repo..."):
            repo.index.add("*")
            if not repo.is_dirty(untracked_files=True):
                console.print("  [yellow]No changes to push[/yellow]")
                return

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            commit_msg = f"chore(vaultit): sync {project_name} -- {timestamp}"
            repo.index.commit(commit_msg)
            repo.remotes.origin.push()

        sha = repo.head.commit.hexsha[:7]
        console.print(f"  [green]Pushed: [bold]{sha}[/bold][/green]")
        console.print(f"\n  [green]Sync complete for [bold]{project_name}[/bold][/green]")
        console.print(f"  [dim]{commit_msg}[/dim]\n")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
