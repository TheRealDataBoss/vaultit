# vaultit — HANDOFF.md
Last updated: 2026-03-10

## What This Is
vaultit is a CLI tool and universal session continuity protocol for AI agents.
Published on PyPI and npm. Zero model drift between AI agents — Claude, GPT, Gemini, any LLM.

## Current State
- PyPI: https://pypi.org/project/vaultit/0.2.1/ ✅ LIVE
- npm: https://www.npmjs.com/package/vaultit ✅ LIVE (v0.2.0, needs 0.2.1 bump)
- GitHub: https://github.com/TheRealDataBoss/vaultit
- Domain: vaultit.ai — PENDING REGISTRATION

## Completed
- [x] Phase 1.5 CLI hardening (enquirer → @inquirer/prompts, config.js, sync.js PAT flow, bootstrap.js clipboard, doctor.js 8-point check, error handling pass)
- [x] Renamed vaultit-ai → agentlock → modelvault → vaultit
- [x] Published vaultit v0.2.0 to npm
- [x] Published vaultit v0.2.0 and v0.2.1 to PyPI
- [x] Rewrote README with badges, problem statement, quickstart, command table
- [x] PyPI trove classifiers — PENDING (CLI tool, not library)

## Active Tasks
- [ ] TASK-0007: Bump npm to v0.2.1 + update npm README to match PyPI
- [ ] TASK-0008: Fix pyproject.toml trove classifiers (Environment::Console, Topic::Utilities, remove library classifier)
- [ ] TASK-0009: Register vaultit.ai domain
- [ ] TASK-0010: Smoke test all 5 CLI commands end to end (init, sync, status, bootstrap, doctor)
- [ ] TASK-0011: Expose Python library API — public functions: bootstrap(), sync(), status(), init() importable from vaultit
- [ ] TASK-0012: Build MCP server — wrap CLI commands as MCP tools (vaultit_bootstrap, vaultit_sync, vaultit_status)
- [ ] TASK-0013: Build REST API (FastAPI) — single backend for MCP + GPT action
- [ ] TASK-0014: Write OpenAPI spec for GPT action distribution
- [ ] TASK-0015: Submit to MCP registry at modelcontextprotocol.io
- [ ] TASK-0016: Build vaultit.ai landing page (HTML already designed, needs hosting — GitHub Pages or Vercel)

## Decisions Made
- Product name: vaultit (final)
- Value prop: Zero model drift between AI agents
- Domain: vaultit.ai (.ai not .dev)
- CLI command: vaultit
- Both PyPI and npm as distribution channels
- Python library API to be exposed (low effort, enables MCP server)
- MCP server is highest leverage next move
- REST API backend enables MCP + GPT action from one codebase
- PyPI token: vaultit-publish2 (entire account scope)

## Architecture (target)
vaultit/
├── CLI (current) ← done
├── Python library API ← TASK-0011
├── MCP server ← TASK-0012
├── REST API (FastAPI) ← TASK-0013
└── GPT action (OpenAPI spec) ← TASK-0014

## Next Session Start
Load this file and STATE_VECTOR.json, confirm task queue, then proceed with TASK-0007.
