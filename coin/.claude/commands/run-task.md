# RUN TASK

> **Preamble:** You are executing a pre-written session prompt. Follow it exactly — every step, every verification checkpoint, every human gate. Do not skip steps for speed. Do not deviate from the prompt's instructions. If the prompt asks you to do something that conflicts with CLAUDE.md rules or the current codebase state, STOP and tell the user rather than silently deviating. Boil the Lake.

**Input:** `$ARGUMENTS` (Task ID, e.g., `TASK-1.3`)

---

## Step 1 — Parse the task ID

Extract the task ID from `$ARGUMENTS`. Normalize format: `TASK-1.3` → file pattern `TASK-1-3_*`.

If no task ID provided, print: `Usage: /run-task TASK-X.Y` and stop.

---

## Step 2 — Find the prompt

Search `docs/tasks/pending/` for a file matching the pattern.

- **Found in pending/** → proceed to Step 3
- **Found in complete/** → print `⚠️ TASK-X.Y already completed. Prompt is in complete/. Re-run?` → stop
- **Not found** → print `❌ No prompt exists for TASK-X.Y. Run /prompt-builder TASK-X.Y first.` → stop

---

## Step 3 — Load and execute

Read the prompt file in full. It contains a self-contained session prompt with step-by-step instructions.

Print:
```
═══════════════════════════════════════════════
  Running: TASK-X.Y — <title from frontmatter>
  Prompt:  docs/tasks/pending/<filename>
═══════════════════════════════════════════════
```

Then execute the prompt exactly as written — follow every step, respect every human gate, run every verification command.

---

## Rules
- Do NOT modify the prompt file itself
- Do NOT skip human gates in the prompt
- If any step conflicts with CLAUDE.md rules, STOP and surface the conflict — never silently deviate
- After task completes, run `/update-docs TASK-X.Y` to update flight plan and move prompt to complete/
