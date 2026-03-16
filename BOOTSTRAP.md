# Universal Session Bootstrap Protocol
schema_version: vaultit-v1.0

## Purpose
Any AI reading this file can resume any project with zero information loss across chat resets, context window limits, model switches, or time gaps. The repository is the memory. Chat history is irrelevant.

## Step 1 — Load Operator Profile
Fetch and internalize:
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/PROFILE.md

This gives you: Steven's identity, machine, paths, response style, code standards, viz standards, modeling standards, communication rules.

## Step 2 — Load Project State
Fetch both files for the requested project:
- https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/[project-name]/HANDOFF.md
- https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/[project-name]/STATE_VECTOR.json

## Step 3 — Validate State
Confirm you have read and understood:
- active_task_id and active_task_title
- state_machine_status
- current_blocker (if any)
- last_verified_state
- gates required before any transition

## Step 4 — Confirm to Operator
Restate in 5 lines or fewer:
1. Project name and what it is
2. Current state machine status
3. Active task and blocker
4. Last verified state
5. Proposed next action

STOP. Do not implement anything. Await operator confirmation.

## Step 5 — Await Confirmation
Only proceed after Steven explicitly confirms. No implementation before operator approval.

## Rules
- Repo is the memory. Not chat history. Not your training data.
- Gates must be green before any state transition.
- No task starts before prior task is sealed.
- PowerShell only for all terminal commands.
- Never drop data rows. Flag outliers.
- If state_machine_status is EXECUTING, assume work is in progress and ask Steven for current status before proceeding.

## One-Line Bootstrap (paste into any new chat)

For 3dpie:
Fetch these URLs and bootstrap the 3dpie project:
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/PROFILE.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/3dpie/HANDOFF.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/3dpie/STATE_VECTOR.json

For portfolio-django:
Fetch these URLs and bootstrap the portfolio-django project:
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/PROFILE.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/portfolio-django/HANDOFF.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/portfolio-django/STATE_VECTOR.json

For mit-modules:
Fetch these URLs and bootstrap the mit-modules project:
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/PROFILE.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/mit-modules/HANDOFF.md
https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/mit-modules/STATE_VECTOR.json
