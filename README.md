# TheRealDataBoss/vaultit
## Universal AI Session Continuity Framework

This repo is the persistent memory layer for all active projects owned by Steven Wazlavek (@theRealDataBoss). Any AI session reads this repo at the start and has full context. No chat history needed. No zip files. No manual re-explanation.

## How To Bootstrap Any Session

Paste this into any new AI chat, replacing [project-name]:

> "Read https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/BOOTSTRAP.md and continue [project-name]"

The AI fetches PROFILE.md + projects/[project]/HANDOFF.md + projects/[project]/STATE_VECTOR.json and is fully loaded in under 60 seconds.

## Structure

| Path | Purpose |
|---|---|
| PROFILE.md | Steven's identity, stack, and all standards |
| BOOTSTRAP.md | Universal session bootstrap protocol for any AI |
| projects/[name]/ | One folder per project — HANDOFF.md + STATE_VECTOR.json |
| standards/ | Authoritative CODE, VIZ, and MODELING standards |
| scripts/ | vaultit_push.ps1 — end-of-session auto-sync |

## Active Projects

| Project | Type | Status |
|---|---|---|
| 3dpie | React/Three.js | EXECUTING TASK-0029 |
| portfolio-django | Django 5 | IDLE |
| mit-modules | Research Notebooks | IDLE |

## Raw Bootstrap URLs

- BOOTSTRAP: https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/BOOTSTRAP.md
- PROFILE: https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/PROFILE.md
- 3dpie HANDOFF: https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/3dpie/HANDOFF.md
- 3dpie STATE: https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/projects/3dpie/STATE_VECTOR.json
