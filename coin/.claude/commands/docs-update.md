# UPDATE DOCS — Update Flight Plan, Prompts & State

> **Preamble:** Docs sync utility. Scope: update flight-plan.md, project-state.md, and prompt files only. Do not modify application code.

Use after finishing one or more tasks. Keeps all records in sync.

---

## Usage

Provide:
- **Task ID(s):** e.g., `TASK-1.3` or `TASK-1.1 TASK-1.2` (space-separated)
- **New status:** defaults to DONE if not specified
- **What was done:** free-form description

**Status pipeline (left → right only, unless BLOCKED):**

| Emoji | Status |
|-------|--------|
| 🔴 | TODO |
| 🟡 | READY (prompt exists) |
| 🔵 | IN PROGRESS |
| 🟠 | NEEDS VERIFICATION |
| 🔶 | BLOCKED |
| ✅ | DONE |

If the user doesn't specify a status, assume `✅ DONE`.

---

## Step 1 — Parse inputs

Extract task IDs, new status, and summary from the user's message.

## Step 2 — Update `docs/flight-plan.md`

For each task:
1. Find the row containing the task ID
2. Replace the current status with the new one
3. If transitioning to ✅ DONE and the Prompt column shows `pending/...`, update it to `complete/...`

Update the flight plan header: `**Updated:** YYYY-MM-DD`

## Step 3 — Move prompt files

For each task marked DONE: check `docs/tasks/pending/` for a matching file and move it to `docs/tasks/complete/`:
```bash
mv docs/tasks/pending/TASK-X-Y_*.md docs/tasks/complete/
```

**Only move on ✅ DONE.** For other status transitions, leave prompts in pending/.

## Step 4 — Update `docs/state/project-state.md`

If the file exists, update two sections:

**4A — Current Status:** Update the status of any in-flight tasks mentioned.

**4B — What Was Just Done:** **Prepend** a new entry (do NOT replace the existing block):
```markdown
## What Was Just Done (YYYY-MM-DD — Session: <name>)

### <Task ID>: <Task Title> → <NEW STATUS>
**Summary:** <description of what was accomplished>
**Prompt:** moved to complete/ (or "no prompt file" if none found)
**Flight plan:** updated docs/flight-plan.md — TASK-X.Y → <status>
```

## Step 5 — Commit

```bash
git add docs/flight-plan.md docs/state/ docs/tasks/
git commit -m "docs: complete TASK-X.Y — <summary>"
```

## Step 6 — Report

```
═══════════════════════════════════════════════
  Task(s) Complete
═══════════════════════════════════════════════
  TASK-1.3 → ✅ DONE
    Prompt: moved to docs/tasks/complete/
  Flight plan updated ✅
  State updated ✅
  Committed: <hash>
═══════════════════════════════════════════════
```

## Rules
- NEVER hard-delete tasks from the flight plan — only change the status
- NEVER move a prompt to complete/ unless status is ✅ DONE
- If a task ID has no row in the flight plan, warn the user — do NOT guess
- This command does NOT run end-session. Wait for the user to run `/end-session` separately.
