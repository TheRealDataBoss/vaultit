# vaultit

[![PyPI version](https://img.shields.io/pypi/v/vaultit?color=00e5ff&labelColor=0d1320)](https://pypi.org/project/vaultit/)
[![Python](https://img.shields.io/pypi/pyversions/vaultit?color=00ffa3&labelColor=0d1320)](https://pypi.org/project/vaultit/)
[![License](https://img.shields.io/pypi/l/vaultit?color=7b61ff&labelColor=0d1320)](https://github.com/TheRealDataBoss/vaultit/blob/main/LICENSE)
[![npm](https://img.shields.io/npm/v/vaultit?color=ffb300&labelColor=0d1320)](https://www.npmjs.com/package/vaultit)

> **Zero model drift between AI agents.**
> Universal session continuity protocol and CLI for Claude, GPT, Gemini, and any LLM.

---

## The Problem

You switch from Claude to GPT mid-project. You open a new chat. You spend 20 minutes re-explaining your stack, your decisions, your constraints. Again. The AI confidently suggests something you already ruled out three sessions ago.

**Every AI session starts with amnesia. vaultit fixes this.**

It gives every project a structured state file — synced to GitHub — that any AI agent can read in under 60 seconds.

---

## Install
```bash
pip install vaultit
# or
npm install -g vaultit
```

---

## How It Works
vaultit init    →  generates STATE_VECTOR.json + HANDOFF.md
vaultit sync    →  pushes state to your GitHub bridge repo
vaultit bootstrap →  generates a paste-ready prompt for any AI
paste it in → full context in < 60 seconds

Works with **Claude**, **ChatGPT**, **Gemini**, **Llama**, **Mistral**, or any LLM that can read a URL.

---

## Quickstart
```bash
cd my-project
vaultit init

# sync state to GitHub
vaultit sync

# generate bootstrap prompt and copy to clipboard
vaultit bootstrap -p my-project --clipboard

# paste into Claude, GPT, Gemini — full context restored instantly
```

---

## Commands

| Command | Description |
|---|---|
| `vaultit init` | Auto-detect project type, generate `STATE_VECTOR.json` + `HANDOFF.md` |
| `vaultit sync` | Push state files to your GitHub bridge repo |
| `vaultit bootstrap` | Generate paste-ready AI prompt, optionally copy to clipboard |
| `vaultit status` | Show all tracked projects in the bridge repo |
| `vaultit doctor` | 8-point health check — token, git, schema, GitHub API |

### init
```bash
vaultit init [-p PROJECT] [-t TYPE] [--bridge REPO]
```

### sync
```bash
vaultit sync [--bridge REPO] [--dry-run]
```

### bootstrap
```bash
vaultit bootstrap -p PROJECT [--bridge REPO] [--clipboard]
```

### status
```bash
vaultit status [--bridge REPO] [--json]
```

### doctor
```bash
vaultit doctor
```

---

## Requirements

- Python 3.10+
- `git` on PATH
- GitHub PAT token (for sync)

---

## License

MIT © [TheRealDataBoss](https://github.com/TheRealDataBoss)
