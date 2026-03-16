"""vaultit doctor -- environment and configuration health check."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from rich.console import Console

console = Console()

PASS = "[green][OK][/green]"
FAIL = "[red][FAIL][/red]"


def run_doctor() -> None:
    """Run the vaultit health check."""
    console.print("\n  [cyan]vaultit doctor[/cyan]\n")

    passed = 0
    failed = 0

    # 1. Python version >= 3.10
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        console.print(f"  {PASS} Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
        passed += 1
    else:
        console.print(f"  {FAIL} Python {py_ver.major}.{py_ver.minor} -- need >= 3.10")
        failed += 1

    # 2. git on PATH
    if shutil.which("git"):
        console.print(f"  {PASS} git found on PATH")
        passed += 1
    else:
        console.print(f"  {FAIL} git not found -- install git and add to PATH")
        failed += 1

    # 3. git user.name configured
    import subprocess

    try:
        name_result = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True
        )
        if name_result.returncode == 0 and name_result.stdout.strip():
            console.print(f"  {PASS} git user.name: {name_result.stdout.strip()}")
            passed += 1
        else:
            console.print(f'  {FAIL} git user.name not set -- run: git config --global user.name "Your Name"')
            failed += 1
    except Exception:
        console.print(f"  {FAIL} could not check git user.name")
        failed += 1

    # 4. git user.email configured
    try:
        email_result = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True
        )
        if email_result.returncode == 0 and email_result.stdout.strip():
            console.print(f"  {PASS} git user.email: {email_result.stdout.strip()}")
            passed += 1
        else:
            console.print(f'  {FAIL} git user.email not set -- run: git config --global user.email "you@example.com"')
            failed += 1
    except Exception:
        console.print(f"  {FAIL} could not check git user.email")
        failed += 1

    # 5. ~/.vaultitrc exists and has token
    rc_path = Path.home() / ".vaultitrc"
    if rc_path.exists():
        try:
            rc_data = json.loads(rc_path.read_text(encoding="utf-8"))
            token = rc_data.get("npm_token") or rc_data.get("token")
            if token:
                console.print(f"  {PASS} GitHub token found in ~/.vaultitrc")
                passed += 1
            else:
                console.print(f"  {FAIL} ~/.vaultitrc exists but no token -- run: vaultit sync to configure")
                failed += 1
        except Exception:
            console.print(f"  {FAIL} ~/.vaultitrc exists but is not valid JSON")
            failed += 1
    else:
        console.print(f"  {FAIL} ~/.vaultitrc not found -- run: vaultit sync to configure")
        failed += 1

    # 6. GitHub API reachable
    try:
        import httpx

        resp = httpx.get("https://api.github.com", timeout=10)
        if resp.status_code == 200:
            console.print(f"  {PASS} GitHub API reachable")
            passed += 1
        else:
            console.print(f"  {FAIL} GitHub API returned {resp.status_code}")
            failed += 1
    except Exception as e:
        console.print(f"  {FAIL} GitHub API unreachable -- {e}")
        failed += 1

    # 7. STATE_VECTOR.json exists in cwd
    cwd = Path.cwd()
    sv_candidates = [
        cwd / "handoff" / "STATE_VECTOR.json",
        cwd / "STATE_VECTOR.json",
    ]
    sv_found = None
    for sv in sv_candidates:
        if sv.exists():
            sv_found = sv
            break

    if sv_found:
        console.print(f"  {PASS} STATE_VECTOR.json found at {sv_found.relative_to(cwd)}")
        passed += 1

        # 8. STATE_VECTOR.json is valid JSON
        try:
            json.loads(sv_found.read_text(encoding="utf-8"))
            console.print(f"  {PASS} STATE_VECTOR.json is valid JSON")
            passed += 1
        except Exception as e:
            console.print(f"  {FAIL} STATE_VECTOR.json is not valid JSON -- {e}")
            failed += 1
    else:
        console.print(f"  {FAIL} STATE_VECTOR.json not found -- run: vaultit init")
        failed += 1

    # Summary
    total = passed + failed
    console.print(f"\n  {passed}/{total} checks passed")
    if failed:
        console.print(f"  [yellow]{failed} issue(s) to fix[/yellow]")
    else:
        console.print("  [green]All checks passed![/green]")
    console.print()
