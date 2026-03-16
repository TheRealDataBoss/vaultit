# Next Task Pointer
schema_version: vaultit-v1.0

- active_task_id: TASK-0029
- title: Drag/merge leaf identity inconsistent after Reset/hard refresh
- status: EXECUTING

First action for new session:
1. cd "C:\Users\Steven\Chart generator\repo\git"
2. npm run dev
3. Open localhost:5173 in real Chrome (not headless)
4. Follow manual QA script in projects/3dpie/HANDOFF.md
5. Identify which step fails and under what conditions
6. Root-cause divergence between Playwright and live UI

Do NOT start Prompt B. Do NOT add telemetry-only tests as proof. Live browser is the only source of truth.
