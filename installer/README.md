# VaultIt — Installers

## Quick Install

### macOS / Linux
```sh
curl -fsSL https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/installer/install.sh | sh
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/installer/install.ps1 | iex
```

## What the Installer Does

1. **Detects your OS** — macOS, Linux, Windows/WSL, or Windows PowerShell
2. **Checks prerequisites** — git (required), node (optional), python (optional)
3. **Clones the vaultit-ai repo** to `~/.vaultit/src/`
4. **Creates a `vaultit` wrapper** in `~/.vaultit/bin/` that delegates to the Node.js or Python CLI
5. **Adds `~/.vaultit/bin/` to your PATH**
6. **Verifies the installation**

## Prerequisites

- **git** — required
- **Node.js 18+** — optional, enables the npm-based CLI
- **Python 3.10+** — optional, enables the Python-based CLI

At least one of Node.js or Python is required for the CLI to function.

## Uninstall

### macOS / Linux
```sh
rm -rf ~/.vaultit
# Remove the PATH line from your .bashrc / .zshrc / .profile
```

### Windows (PowerShell)
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.vaultit"
# Remove the PATH entry from User environment variables
```

## Alternative: Install via Package Managers

### npm
```sh
npm install -g vaultit-ai
```

### pip
```sh
pip install vaultit-ai
```
