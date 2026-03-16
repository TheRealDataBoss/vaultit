# Universal Bootstrap Protocol
schema_version: vaultit-v1.0

## Purpose

This protocol enables any AI assistant to resume any project with zero information loss. It is model-agnostic — it works identically with Claude, GPT, Gemini, LLaMA, Mistral, or any future model. The repository is the single source of truth. Chat history is irrelevant.

## Step 1 — Load Operator Profile

Fetch and internalize the operator's PROFILE.md from the bridge repository. This contains:
- Identity and contact
- Machine specs and OS
- Shell preference (critical — never guess)
- Key file paths
- Response style requirements
- Code, visualization, and modeling standards
- Communication rules

Do not proceed until PROFILE.md is fully loaded and understood.

## Step 2 — Load Project State

Fetch both state files for the requested project:
- `projects/[project-name]/HANDOFF.md` — human-readable context
- `projects/[project-name]/STATE_VECTOR.json` — machine-readable state

Both files are required. If either is missing, report the error and stop.

## Step 3 — Validate State

Confirm you have read and understood all of the following:

| Field | What to check |
|---|---|
| `schema_version` | Must match a version you can parse |
| `state_machine_status` | Current lifecycle state |
| `active_task_id` | The task in progress (may be null) |
| `active_task_title` | Human-readable task name |
| `current_blocker` | What is blocking progress (may be null) |
| `last_verified_state` | The last known-good state |
| `gates` | Commands that must pass before transitions |
| `last_updated` | How stale the state is |

If `state_machine_status` is **EXECUTING**: assume work is actively in progress. Do NOT assume you know the current situation. Ask the operator what has changed since `last_updated`.

If `state_machine_status` is **PROTOCOL_BREACH**: an illegal state transition was detected. Do NOT proceed with normal work. Report the breach to the operator and await instructions for resolution.

If `last_updated` is more than 7 days old: warn the operator that state may be stale and ask for confirmation before proceeding.

## Step 4 — Confirm to Operator

Restate the project context in exactly 5 lines:

1. **Project**: [name] — [one-sentence description]
2. **Status**: [state_machine_status]
3. **Task**: [active_task_id] — [active_task_title] | Blocker: [current_blocker or "None"]
4. **Last verified**: [last_verified_state]
5. **Proposed action**: [what you would do next, based on state]

## Step 5 — Await Confirmation

**STOP.** Do not implement anything. Do not write code. Do not run commands. Do not modify files.

Wait for the operator to explicitly confirm before taking any action. The operator may:
- Confirm and proceed
- Correct the state (update your understanding)
- Redirect to a different task
- Provide additional context not in the state files

Only proceed after explicit confirmation.

## Rules

1. **The repository is the memory.** Not chat history. Not training data. Not previous conversations. If it is not in the repo, it does not exist.

2. **Gates are mandatory.** Every gate command in the `gates` array must exit 0 before any state transition is legal. No exceptions. No shortcuts.

3. **No task starts before the prior task is sealed.** If `state_machine_status` is EXECUTING, that task must reach SEALED or VERIFIED before a new task begins.

4. **Respect the operator's shell.** Check PROFILE.md for shell preference. Never assume bash. Never assume PowerShell. Use what the operator specifies.

5. **Never drop data rows.** Flag anomalies with boolean columns. Preserve all original data.

6. **State transitions must be legal.** The valid transitions are:
   - IDLE → PROPOSED
   - PROPOSED → EXECUTING
   - EXECUTING → AWAITING_REVIEW
   - AWAITING_REVIEW → REVIEWED
   - REVIEWED → AWAITING_MANUAL_VALIDATION
   - AWAITING_MANUAL_VALIDATION → VALIDATED
   - VALIDATED → AWAITING_SEAL
   - AWAITING_SEAL → SEALED
   - SEALED → VERIFIED
   - VERIFIED → IDLE
   - Any state → PROTOCOL_BREACH (on illegal transition)

7. **Update STATE_VECTOR.json at every transition.** The state file must always reflect reality.

8. **Report, don't hide.** If something fails, if gates don't pass, if state is inconsistent — report it immediately. Never silently proceed past a failure.
