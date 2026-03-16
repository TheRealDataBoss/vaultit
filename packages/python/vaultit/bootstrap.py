"""vaultit bootstrap — generate paste-ready AI bootstrap prompt."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo
from rich.console import Console
from rich.panel import Panel

console = Console()


def _load_config(cwd: Path) -> dict | None:
    config_path = cwd / ".vaultit"
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def _copy_to_clipboard(text: str) -> bool:
    """Attempt to copy text to the system clipboard. Returns True on success."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif system == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
        else:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode(),
                check=True,
            )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_bootstrap(
    project: str,
    bridge: str | None = None,
    clipboard: bool = False,
) -> None:
    """Generate a paste-ready bootstrap prompt for any AI chat."""
    cwd = Path.cwd()
    config = _load_config(cwd)
    bridge_repo = bridge or (config and config.get("bridge_repo"))

    console.print("\n  [cyan]vaultit bootstrap[/cyan]\n")

    if not bridge_repo:
        console.print("  [red]No bridge repo configured. Run vaultit init or pass --bridge.[/red]")
        raise SystemExit(1)

    # Verify the project exists
    tmp_dir = Path(tempfile.mkdtemp(prefix="vaultit-"))
    try:
        bridge_url = f"https://github.com/{bridge_repo}.git"

        with console.status("Verifying project in bridge repo..."):
            Repo.clone_from(bridge_url, str(tmp_dir), depth=1)

        project_dir = tmp_dir / "projects" / project
        if not project_dir.exists():
            console.print(f'  [red]Project "{project}" not found in bridge repo.[/red]')
            projects_dir = tmp_dir / "projects"
            if projects_dir.exists():
                available = [d.name for d in projects_dir.iterdir() if d.is_dir()]
                if available:
                    console.print(f"  [dim]Available: {', '.join(available)}[/dim]")
            raise SystemExit(1)

        sv_path = project_dir / "STATE_VECTOR.json"
        if not sv_path.exists():
            console.print(f"  [red]No STATE_VECTOR.json found for {project}[/red]")
            raise SystemExit(1)

        console.print(f'  [green]Project "{project}" verified[/green]')

        # Build bootstrap prompt with all URLs explicit
        base_url = f"https://raw.githubusercontent.com/{bridge_repo}/main"
        urls = [
            f"{base_url}/PROFILE.md",
            f"{base_url}/projects/{project}/HANDOFF.md",
            f"{base_url}/projects/{project}/STATE_VECTOR.json",
        ]

        prompt_lines = [
            f"Fetch these URLs and bootstrap the {project} project:",
            *urls,
        ]
        prompt = "\n".join(prompt_lines)

        console.print("\n  Paste this into any new AI chat:\n")
        console.print(Panel(prompt, border_style="green", padding=(1, 2)))

        if clipboard:
            if _copy_to_clipboard(prompt):
                console.print("  [green]Copied to clipboard![/green]")
            else:
                console.print("  [yellow]Could not copy to clipboard. Copy manually from above.[/yellow]")

        console.print()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
