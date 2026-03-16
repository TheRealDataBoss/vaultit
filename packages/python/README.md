# vaultit

mcp-name: io.github.TheRealDataBoss/vaultit

[![PyPI](https://img.shields.io/pypi/v/vaultit?color=00d4ff&labelColor=0a0a0a)](https://pypi.org/project/vaultit/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/vaultit?color=6acc65&labelColor=0a0a0a)](https://pypi.org/project/vaultit/)
[![License: MIT](https://img.shields.io/pypi/l/vaultit?color=7b61ff&labelColor=0a0a0a)](https://github.com/TheRealDataBoss/vaultit/blob/main/LICENSE)
[![MCP Native](https://img.shields.io/badge/MCP-native-00d4ff?labelColor=0a0a0a)](https://registry.modelcontextprotocol.io)

> **Zero model drift between AI agents.**

---

## Install

```bash
pip install vaultit
```

## Quickstart

```bash
vaultit init
vaultit sync --agent claude
vaultit bootstrap --clipboard
# paste into any AI — full context restored
```

## CLI Reference

| Command | Description |
|---|---|
| `init` | Scaffold project context — state vector, conventions, tasks |
| `sync` | Scan repo and update state vector with current project state |
| `bootstrap` | Generate paste-ready briefing for any AI agent |
| `status` | Show tracked projects and their current state |
| `doctor` | Validate context files for consistency and missing fields |
| `migrate` | Run database schema migrations |
| `export` | Export project context to JSON/Markdown |
| `diff` | Show what changed since last sync |
| `serve` | Start the REST API server (FastAPI + Uvicorn) |
| `sessions` | List and manage agent sessions |
| `tasks` | List and manage project tasks |
| `decisions` | List and manage architectural decisions |
| `auth` | Create and revoke API keys (`ck_` prefix, SHA-256 stored) |

## Python SDK

```python
from vaultit import VaultItClient

client = VaultItClient()

# Sessions
session = client.create_session(agent="claude", project="myproject")
client.end_session(session.id, summary="Implemented auth module")

# Tasks & decisions
client.create_task(project="myproject", title="Add rate limiting")
client.create_decision(project="myproject", title="Use PostgreSQL", rationale="Need JSONB")

# Handoff
handoff = client.create_handoff(from_session=s1.id, to_agent="gpt-4")
```

## MCP Server

10 tools — native Claude Code integration via [Model Context Protocol](https://modelcontextprotocol.io).

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vaultit": {
      "command": "python",
      "args": ["-m", "vaultit.mcp"]
    }
  }
}
```

## Backends

```bash
# File (default) — zero config
vaultit init

# SQLite
vaultit init --backend sqlite

# PostgreSQL
vaultit init --backend postgres --db-url postgresql://user:pass@localhost/ck
```

## REST API

14 endpoints + 3 auth endpoints. FastAPI with OpenAPI spec.

```bash
vaultit serve --port 8420
# → http://localhost:8420/docs   (Swagger UI)
# → http://localhost:8420/openapi.json
```

Auth header: `Authorization: Bearer ck_your_api_key`

## Multi-Agent Coordination

Three modes for concurrent agent access:

- **sequential** — one agent at a time (default)
- **lock-based** — pessimistic locking per resource
- **merge** — optimistic merge with conflict resolution

## Links

- [GitHub](https://github.com/TheRealDataBoss/vaultit)
- [Docs](https://therealdataboss.github.io/vaultit)
- [PyPI](https://pypi.org/project/vaultit/)
- [MCP Registry](https://registry.modelcontextprotocol.io)

## License

MIT © [TheRealDataBoss](https://github.com/TheRealDataBoss)
