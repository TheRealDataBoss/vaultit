"""
vaultit Python library API.

Example usage:
    from vaultit import bootstrap, sync, status, init

    # Initialize state files in current project
    init(project="my-project", bridge="user/vaultit")

    # Sync state to GitHub
    sync(bridge="user/vaultit", dry_run=False)

    # Get status of all projects
    projects = status(bridge="user/vaultit")

    # Generate bootstrap prompt
    prompt = bootstrap(project="my-project", bridge="user/vaultit", clipboard=False)
"""

from pathlib import Path
import subprocess
import sys
import json


def init(project: str = None, bridge: str = None, project_type: str = None) -> dict:
    """
    Initialize vaultit state files in the current directory.

    Args:
        project: Project slug (default: current directory name)
        bridge: GitHub bridge repo e.g. 'username/vaultit'
        project_type: Override project type detection

    Returns:
        dict with keys: project, state_vector_path, handoff_path, success
    """
    args = [sys.executable, "-m", "vaultit.cli", "init"]
    if project:
        args += ["-p", project]
    if bridge:
        args += ["--bridge", bridge]
    if project_type:
        args += ["-t", project_type]

    result = subprocess.run(args, capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "project": project or Path.cwd().name,
    }


def sync(bridge: str = None, dry_run: bool = False) -> dict:
    """
    Sync state files to the GitHub bridge repo.

    Args:
        bridge: GitHub bridge repo e.g. 'username/vaultit'
        dry_run: Preview without pushing

    Returns:
        dict with keys: success, stdout, stderr
    """
    args = [sys.executable, "-m", "vaultit.cli", "sync"]
    if bridge:
        args += ["--bridge", bridge]
    if dry_run:
        args += ["--dry-run"]

    result = subprocess.run(args, capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def status(bridge: str = None) -> dict:
    """
    Get status of all projects in the bridge repo.

    Args:
        bridge: GitHub bridge repo e.g. 'username/vaultit'

    Returns:
        dict with keys: success, projects (list), raw
    """
    args = [sys.executable, "-m", "vaultit.cli", "status", "--json"]
    if bridge:
        args += ["--bridge", bridge]

    result = subprocess.run(args, capture_output=True, text=True)
    projects = []
    try:
        projects = json.loads(result.stdout)
    except Exception:
        pass

    return {
        "success": result.returncode == 0,
        "projects": projects,
        "raw": result.stdout.strip(),
    }


def bootstrap(project: str, bridge: str = None, clipboard: bool = False) -> str:
    """
    Generate a paste-ready bootstrap prompt for any AI chat.

    Args:
        project: Project slug (required)
        bridge: GitHub bridge repo e.g. 'username/vaultit'
        clipboard: Copy prompt to clipboard

    Returns:
        str — the bootstrap prompt text
    """
    args = [sys.executable, "-m", "vaultit.cli", "bootstrap", "-p", project]
    if bridge:
        args += ["--bridge", bridge]
    if clipboard:
        args += ["--clipboard"]

    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout.strip()


def doctor() -> dict:
    """
    Run the vaultit health check.

    Returns:
        dict with keys: success, checks (list), stdout
    """
    args = [sys.executable, "-m", "vaultit.cli", "doctor"]
    result = subprocess.run(args, capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
