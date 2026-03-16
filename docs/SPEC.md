# VaultIt — Protocol Specification
Version: 0.1.0

## What VaultIt Is

VaultIt is a universal session continuity protocol and toolset that gives developers deterministic, lossless context transfer across AI chat sessions, models, projects, and time. It replaces ad-hoc "here's the context" pasting with a structured, version-controlled, machine-readable state system that any AI assistant can consume in under 60 seconds.

## The Core Problem

AI chat sessions are ephemeral. When a session ends — whether by context window exhaustion, model switch, browser crash, or overnight break — all accumulated context is lost. Developers compensate by re-explaining, re-pasting, attaching zip files, or maintaining personal notes. This is manual, error-prone, and scales to zero projects.

VaultIt solves this by making the git repository the memory. State is structured. Handoffs are standardized. Bootstrap is automated. The AI reads the repo and knows everything.

## Protocol Overview

The protocol operates on three layers:

### Layer 1 — Schema
`STATE_VECTOR.json` is a JSON document conforming to `vaultit.schema.json` (JSON Schema draft-07). It captures the machine-readable state of a project: what stage it is in, what task is active, what is blocking progress, and what commands must pass before any transition.

### Layer 2 — Tooling
CLI tools (`vaultit init`, `vaultit sync`, `vaultit status`, `vaultit bootstrap`) automate the creation, validation, synchronization, and consumption of state files. Available as npm package (`vaultit-ai`) and Python package (`vaultit-ai`).

### Layer 3 — Bootstrap
A standardized protocol document (`BOOTSTRAP.protocol.md`) that any AI assistant can follow to load operator context, project state, and task details in a deterministic sequence.

## STATE_VECTOR.json Specification

### Required Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Protocol version. Pattern: `vaultit-v<major>.<minor>` |
| `project` | string | URL-safe project slug. Used as directory name in bridge repo. |
| `project_type` | enum | One of: `web_app`, `ml_pipeline`, `research_notebook`, `data_pipeline`, `mobile_app`, `cli_tool`, `library`, `course_module`, `other` |
| `local_path` | string | Absolute path to project root on operator's machine |
| `state_machine_status` | enum | Current lifecycle state (see State Machine section) |
| `active_task_id` | string\|null | Task identifier (e.g. `TASK-0029`). Null when IDLE. |
| `active_task_title` | string\|null | Human-readable task title. Null when IDLE. |
| `current_blocker` | string\|null | What is blocking progress. Null when unblocked. |
| `last_verified_state` | string | Description of last state where all gates passed |
| `gates` | string[] | Shell commands that must exit 0 before any state transition |
| `last_updated` | date | ISO 8601 date of last update |

### Optional Fields

| Field | Type | Description |
|---|---|---|
| `repo` | string | GitHub URL or `"local only"` |
| `branch` | string\|null | Active git branch |
| `repo_head_sha` | string\|null | Short SHA of latest commit |
| `effective_verified_sha` | string\|null | Short SHA of last commit passing all gates |
| `environment` | object | `{ language, version, package_manager, venv_path }` |
| `team` | object | `{ executor, auditor, operator }` |

### Validation

STATE_VECTOR.json must validate against `protocol/vaultit.schema.json`. The schema enforces `additionalProperties: false` — unrecognized fields are rejected.

## HANDOFF.md Specification

HANDOFF.md is the human-readable companion to STATE_VECTOR.json. It provides narrative context that structured data cannot capture.

### Required Sections

| Section | Purpose |
|---|---|
| **What It Is** | One paragraph describing the project |
| **Where It Is** | Local path, repo URL, active branch |
| **Current Status** | State machine status and active task |
| **Active Blocker** | What is preventing progress (or "None") |
| **Non-Negotiables** | Project invariants that must never be violated |
| **Gates** | Exact shell commands required before transitions |
| **Environment Setup** | How to run the project from scratch |
| **Next Action** | The single next thing to do |

## Bootstrap Protocol

The bootstrap protocol is a 5-step deterministic sequence:

1. **Load Operator Profile** — Fetch PROFILE.md. Internalize identity, machine, standards, communication rules.
2. **Load Project State** — Fetch HANDOFF.md and STATE_VECTOR.json for the target project.
3. **Validate State** — Check all required fields. Handle special statuses (EXECUTING, PROTOCOL_BREACH, stale dates).
4. **Confirm to Operator** — Restate context in exactly 5 lines.
5. **Await Confirmation** — Do not act until the operator explicitly approves.

## State Machine

### States

| State | Meaning |
|---|---|
| `IDLE` | No active task. Ready for new work. |
| `PROPOSED` | Task has been proposed but not started. |
| `EXECUTING` | Task is actively being worked on. |
| `AWAITING_REVIEW` | Work complete, waiting for code review. |
| `REVIEWED` | Code review passed. |
| `AWAITING_MANUAL_VALIDATION` | Waiting for operator to manually validate. |
| `VALIDATED` | Manual validation passed. |
| `AWAITING_SEAL` | Ready to be sealed (final commit, changelog). |
| `SEALED` | Task is sealed. No further changes. |
| `VERIFIED` | Verified in production or final environment. |
| `PROTOCOL_BREACH` | Illegal transition detected. Requires manual resolution. |

### Legal Transitions

```
IDLE → PROPOSED → EXECUTING → AWAITING_REVIEW → REVIEWED
→ AWAITING_MANUAL_VALIDATION → VALIDATED → AWAITING_SEAL
→ SEALED → VERIFIED → IDLE
```

Any state may transition to `PROTOCOL_BREACH` when an illegal transition is attempted.

Not every project uses every state. Lightweight projects may go `IDLE → EXECUTING → SEALED → IDLE`. The protocol enforces order, not completeness.

## Gate Contract

Gates are shell commands listed in `STATE_VECTOR.json.gates`. They encode the project's definition of "working."

**Rules:**
- Every gate must exit 0 before any state transition
- Gates run sequentially in array order
- A failing gate blocks all transitions
- Gates are project-specific (tests, builds, linters, clean git status)
- Gates are never skipped, even in emergencies

**Examples:**
```
["npm test", "npm run build", "git status"]
["python manage.py check", "python manage.py test"]
["npx vitest run", "npx playwright test", "npm run build:check"]
```

## Versioning

The protocol uses semantic versioning in `schema_version`:
- **Major** version: breaking schema changes (fields removed or type-changed)
- **Minor** version: additive changes (new optional fields)

Consumers must check `schema_version` before parsing. Unknown major versions must be rejected. Unknown minor versions with the same major may be parsed with a warning.

## Extension Points

The schema is strict (`additionalProperties: false`), but extensible through:
1. **New optional fields** added in minor versions
2. **Project-type-specific templates** that layer on top of the base schema
3. **Custom gate commands** that encode any project-specific invariant

## Model Compatibility

This protocol works with any AI assistant that can:
1. Fetch URLs or read files
2. Parse JSON
3. Follow structured instructions

Tested targets: Claude (Anthropic), GPT-4 (OpenAI), Gemini (Google), open-weight models via API. The protocol contains no model-specific instructions.
