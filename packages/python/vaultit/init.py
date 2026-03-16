"""vaultit init — initialize state files in the current project."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import questionary
from rich.console import Console

console = Console()

PROJECT_TYPE_SIGNALS: list[tuple[str, str, str]] = [
    ("manage.py", "web_app", "Django web app"),
    ("next.config.js", "web_app", "Next.js web app"),
    ("next.config.mjs", "web_app", "Next.js web app"),
    ("vite.config.ts", "web_app", "Vite web app"),
    ("vite.config.js", "web_app", "Vite web app"),
    ("Cargo.toml", "cli_tool", "Rust project"),
    ("setup.py", "library", "Python library"),
    ("pyproject.toml", "library", "Python project"),
    ("requirements.txt", "ml_pipeline", "Python ML pipeline"),
    ("package.json", "web_app", "Node.js project"),
]

DEFAULT_GATES: dict[str, list[str]] = {
    "web_app": ["npm test", "npm run build", "git status"],
    "ml_pipeline": ["python -m pytest", "git status"],
    "research_notebook": ["jupyter nbconvert --execute --to notebook", "git status"],
    "data_pipeline": ["python -m pytest", "git status"],
    "mobile_app": ["npm test", "npm run build", "git status"],
    "cli_tool": ["npm test", "npm run build", "git status"],
    "library": ["python -m pytest", "git status"],
    "course_module": ["jupyter nbconvert --execute --to notebook", "git status"],
    "other": ["git status"],
}


def detect_project_type(directory: Path) -> tuple[str, str]:
    """Detect project type by inspecting files in the directory."""
    for filename, ptype, label in PROJECT_TYPE_SIGNALS:
        if (directory / filename).exists():
            return ptype, f"{label} (found {filename})"

    # Check for notebooks
    notebooks = list(directory.glob("*.ipynb"))
    if notebooks:
        return "research_notebook", f"Research notebook ({len(notebooks)} .ipynb files)"

    return "other", "Unknown project type"


def init_project(
    project: str | None = None,
    project_type: str | None = None,
    bridge: str | None = None,
) -> None:
    """Initialize vaultit state files in the current project."""
    cwd = Path.cwd()
    project_name = project or cwd.name

    console.print("\n  [cyan]vaultit init[/cyan]\n")

    # Detect project type
    detected_type, detected_label = detect_project_type(cwd)
    console.print(f"  [green]Detected:[/green] {detected_label}")
    resolved_type = project_type or detected_type

    # Prompt for bridge repo
    bridge_repo = bridge
    if not bridge_repo:
        bridge_repo = questionary.text(
            "Bridge repo (e.g. yourname/vaultit):"
        ).ask()

    # Create directories
    handoff_dir = cwd / "handoff"
    docs_dir = cwd / "docs"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    gates = DEFAULT_GATES.get(resolved_type, ["git status"])

    # Generate STATE_VECTOR.json
    state_vector = {
        "schema_version": "vaultit-v1.0",
        "project": project_name,
        "project_type": resolved_type,
        "local_path": str(cwd),
        "state_machine_status": "IDLE",
        "active_task_id": None,
        "active_task_title": None,
        "current_blocker": None,
        "last_verified_state": "Initial project setup",
        "gates": gates,
        "last_updated": date.today().isoformat(),
        "repo": f"https://github.com/{bridge_repo}" if bridge_repo else "local only",
        "branch": "main",
        "repo_head_sha": None,
        "effective_verified_sha": None,
    }

    sv_path = handoff_dir / "STATE_VECTOR.json"
    sv_path.write_text(json.dumps(state_vector, indent=2) + "\n", encoding="utf-8")
    console.print(f"  [green]Created:[/green] {sv_path}")

    # Generate HANDOFF.md
    handoff_content = f"""# {project_name} — Project Handoff
schema_version: vaultit-v1.0

## What It Is
[FILL IN: Describe this project in one paragraph.]

## Where It Is
- Local: {cwd}
- GitHub: {state_vector['repo']}
- Branch: main

## Current Status
State machine: IDLE. No active task.

## Active Blocker
None

## Non-Negotiables
- [FILL IN: List project invariants]

## Gates
{chr(10).join(f'- {g}' for g in gates)}

## Environment Setup
[FILL IN: Steps to run from a clean clone]

## Next Action
[FILL IN: First task to work on]
"""

    handoff_path = docs_dir / "HANDOFF.md"
    handoff_path.write_text(handoff_content, encoding="utf-8")
    console.print(f"  [green]Created:[/green] {handoff_path}")

    # Write .vaultit config
    config = {
        "bridge_repo": bridge_repo,
        "project_name": project_name,
        "state_vector_path": "handoff/STATE_VECTOR.json",
        "handoff_path": "docs/HANDOFF.md",
    }
    config_path = cwd / ".vaultit"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    console.print(f"  [green]Created:[/green] {config_path}")

    console.print("\n  [cyan]Next steps:[/cyan]")
    console.print("  1. Fill in the [FILL IN] sections in docs/HANDOFF.md")
    console.print("  2. Review handoff/STATE_VECTOR.json")
    console.print("  3. Run: [bold]vaultit sync[/bold] to push to your bridge repo\n")
