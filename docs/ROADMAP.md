# VaultIt — Roadmap

## v0.1.0 — Protocol Foundation (current)
- JSON Schema draft-07 for STATE_VECTOR.json
- Annotated templates for STATE_VECTOR.json and HANDOFF.md
- Model-agnostic bootstrap protocol
- npm CLI scaffold (vaultit-ai)
- Python CLI scaffold (vaultit-ai)
- POSIX and PowerShell installers
- GitHub Action for automated sync
- Human-readable protocol spec

## v0.2.0 — CLI Polish + Registry Publish
- End-to-end test suites for both CLIs
- Schema validation integrated into sync command
- Interactive init wizard with project-type presets
- Publish to npm registry
- Publish to PyPI
- Man pages and shell completions (bash, zsh, PowerShell)

## v0.3.0 — GitHub Action Marketplace
- Publish Action to GitHub Marketplace
- Automatic STATE_VECTOR.json generation from CI metadata
- PR comment bot: posts bootstrap prompt on new PRs
- Branch-aware state tracking (sync per-branch state)

## v0.4.0 — VS Code Extension
- Sidebar panel showing current project state
- One-click bootstrap prompt generation
- Inline gate status indicators
- STATE_VECTOR.json editor with schema validation
- HANDOFF.md preview with section linting

## v1.0.0 — Stable Protocol + Team Sharing
- Protocol schema frozen at v1.0
- Multi-operator support: team members share a bridge repo
- Role-based state transitions (executor, auditor, operator)
- Conflict resolution for concurrent state updates
- Hosted bridge option (vaultit.ai SaaS) as alternative to GitHub bridge repo
- Migration tooling from v0.x to v1.0

## Future
- Enterprise tier: SSO, audit logs, compliance controls
- Analytics dashboard: session frequency, context load time, state transition velocity
- Multi-agent support: multiple AI executors coordinating via shared state
- IDE plugins: JetBrains, Neovim, Cursor
- Protocol adapters: Jira, Linear, Notion sync for task metadata
- Offline-first mobile companion for state inspection
