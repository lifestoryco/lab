---
description: Sync docs after finishing a task. Updates the roadmap in project-state.md, moves prompt files from pending/ to complete/, and commits. Does NOT run end-session — call that separately.
---

# /docs-update

Docs sync utility. Run after finishing one or more tasks.
Scope: `docs/state/project-state.md` and prompt files only. Never touches application code.

---

## Usage

```
/docs-update H-1.2
/docs-update H-1.2 H-1.3
/docs-update H-1.2 blocked
/docs-update H-1.3 in-progress
```

Provide:
- **Task ID(s):** e.g. `H-1.2` or `H-1.2 H-1.3` (space-separated)
- **New status:** defaults to `✅ DONE` if not specified

**Status pipeline (left → right only, unless BLOCKED):**

| Emoji | Status | Meaning |
|-------|--------|---------|
| 🔴 | TODO | Not started |
| 🟡 | READY | Prompt exists in pending/ |
| 🔵 | IN PROGRESS | Currently being worked |
| 🟠 | NEEDS VERIFICATION | Work done, awaiting check |
| 🔶 | BLOCKED | Waiting on dependency |
| ✅ | DONE | Complete |

If no status is specified, assume `✅ DONE`.

---

## Step 1 — Parse inputs

Extract task IDs, new status, and any summary description from `$ARGUMENTS`.

Normalize task ID format: `H-1.2` → file pattern `H-1-2_*`

---

## Step 2 — Update the roadmap in `docs/state/project-state.md`

For each task ID:

1. Find the matching row in the **Roadmap** table (the `| H-X.Y | ... |` row)
2. Replace the **Status** column value with the new status emoji + label
3. If no matching row is found: warn the user — do NOT guess or add a new row silently

Also update the file header line:
```
*Keep this file current. The advisory board reads it at the start of every meeting.*
```
Add or update a last-updated note directly below it:
```
*Last updated: YYYY-MM-DD*
```

---

## Step 3 — Move prompt files

For each task marked `✅ DONE`:

```bash
# Find and move matching prompt
ls docs/tasks/prompts/pending/H-X-Y_* 2>/dev/null
mv docs/tasks/prompts/pending/H-X-Y_*.md docs/tasks/prompts/complete/
```

- If found → move and note the filename in the report
- If not found → note "no prompt file" in the report (not an error — some tasks have no prompt)
- **Only move on ✅ DONE.** Leave prompts in pending/ for all other status transitions.

---

## Step 4 — Prepend a "What Was Just Done" block

In `docs/state/project-state.md`, **prepend** a new entry immediately after the `---` separator
that follows "What Holo Is". Do NOT replace the existing "What Was Just Done" block — stack them.

```markdown
## What Was Just Done (YYYY-MM-DD)

### H-X.Y: {Task Title} → ✅ DONE
**Summary:** {description of what was accomplished}
**Prompt:** moved to docs/tasks/prompts/complete/{filename}  ← or "no prompt file"
**Roadmap:** updated Status column in project-state.md → ✅ DONE
```

---

## Step 5 — Commit

```bash
git add docs/state/project-state.md docs/tasks/prompts/
git commit -m "docs: complete H-X.Y — {short summary}"
```

Use `docs:` prefix. One commit per `/docs-update` call regardless of how many tasks.

---

## Step 6 — Report

```
═══════════════════════════════════════════════
  Docs Updated
═══════════════════════════════════════════════
  H-1.2 → ✅ DONE
    Prompt: moved to docs/tasks/prompts/complete/
  H-1.3 → 🔵 IN PROGRESS
    Prompt: remains in pending/
  Roadmap updated ✅
  State updated ✅
  Committed: {hash}
═══════════════════════════════════════════════
```

---

## Rules

- NEVER hard-delete tasks from the roadmap — only change the status
- NEVER move a prompt to complete/ unless status is ✅ DONE
- NEVER touch application code (api/, pokequant/, config.py, tests/, HoloPage.tsx)
- If a task ID has no matching roadmap row, warn — do NOT guess
- This command does NOT run end-session. Call `/end-session` separately when ready to push.
