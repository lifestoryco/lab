---
description: Execute a pre-written holo task prompt from docs/tasks/prompts/pending/. Follow every step exactly — no skipping, no deviating. Use after /prompt-builder has generated the task file.
---

# /run-task

Execute a pre-written session prompt exactly as written.

**Input:** `$ARGUMENTS` — Task ID, e.g. `H-1.2` or `H-2.1`

---

## Step 1 — Parse the task ID

Extract the task ID from `$ARGUMENTS`. Normalize format:
- `H-1.2` → file pattern `H-1-2_*`
- `H-2.1` → file pattern `H-2-1_*`

If no task ID provided, print:
```
Usage: /run-task H-X.Y
Example: /run-task H-1.2
```
And stop.

---

## Step 2 — Find the prompt file

```bash
ls docs/tasks/prompts/pending/H-X-Y_* 2>/dev/null
ls docs/tasks/prompts/complete/H-X-Y_* 2>/dev/null
```

- **Found in pending/** → proceed to Step 3
- **Found in complete/** → print:
  ```
  ⚠️  H-X.Y is already marked complete.
  Prompt is in docs/tasks/prompts/complete/
  Re-run anyway? (yes/no)
  ```
  Wait for confirmation before proceeding.
- **Not found anywhere** → print:
  ```
  ❌ No prompt exists for H-X.Y.
  Run /prompt-builder H-X.Y to generate one first.
  ```
  And stop.

---

## Step 3 — Load and execute

Read the full prompt file. It is self-contained with step-by-step instructions.

Print:
```
═══════════════════════════════════════════════
  Running: H-X.Y — {title from frontmatter}
  Prompt:  docs/tasks/prompts/pending/{filename}
═══════════════════════════════════════════════
```

Execute the prompt **exactly as written**:
- Follow every step in order
- Respect every HUMAN GATE — pause and wait for confirmation
- Run every verification command listed
- If any step conflicts with CLAUDE.md rules or the current codebase state,
  **STOP** and surface the conflict — never silently deviate

---

## Step 4 — Post-completion

When all steps in the prompt are complete:

1. Run the verification suite:
   ```bash
   .venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -20
   ```

2. Move the completed prompt:
   ```bash
   mv docs/tasks/prompts/pending/H-X-Y_*.md docs/tasks/prompts/complete/
   ```

3. Update `docs/state/project-state.md` — mark the task as ✅ COMPLETE in the roadmap table
   and add a "What Was Just Done" block at the top.

4. Confirm:
   ```
   ✅ H-X.Y complete — prompt moved to docs/tasks/prompts/complete/
   Tests: {N passed}
   ```

## Rules

- Do NOT modify the prompt file during execution
- Do NOT skip HUMAN GATES in the prompt
- Do NOT batch unrelated changes — one logical change per commit
- If the test suite fails after completion, fix before moving the prompt to complete/
- Always update project-state.md after a task completes
