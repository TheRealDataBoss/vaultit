# 3dpie — Project Handoff
schema_version: vaultit-v1.0

## What It Is
React + Three.js (R3F) 3D chart generator. Pie and bar charts with per-element controls, recursive sub-element engine, selective bloom, XR-ready architecture, and DEL-v2 formal state machine governance. Portfolio/hobby project.

## Where It Is
- Local: C:\Users\Steven\Chart generator\repo\git
- GitHub: https://github.com/TheRealDataBoss/3dpie
- Branch: fix/controls-bloom-recovery

## Current Status
State machine: EXECUTING
Active task: TASK-0029 — Drag/merge leaf identity inconsistent after Reset/hard refresh

## Active Blocker
Playwright 244/244 pass but Steven's manual QA fails. Root cause unknown. Suspected: DomDragController pointer capture leaks state across Leva reset (programmatic navigation) and F5 hard refresh. InteractionController FSM may not fully reset. R3F onPointerDown instanceId resolution differs between headless Chromium and real browser.

## Non-Negotiables
- Desktop behavior unchanged by default
- XR mode (?mode=xr) must load
- No console spam — diagnostics strictly opt-in
- build:check must pass (bundle size budget)
- State machine transitions must be legal

## Gates (must be green before any transition)
- npx vitest run
- npx playwright test
- npm run build:check
- git status (clean tree)

## Next Action
Read projects/3dpie/NEXT_TASK.md
