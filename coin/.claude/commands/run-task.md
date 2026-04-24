---
description: Execute a pending task prompt step-by-step. Reads the prompt file, implements it, verifies, and reports.
---

# /run-task [task-id]

**Usage:** `/run-task S-1.2`

---

## Steps

1. Find the prompt file: `docs/tasks/prompts/pending/{task-id}_*.md`
   - If not found: `❌ No prompt for {task-id} — run /prompt-builder {task-id} first`
2. Read the prompt file in full
3. Confirm acceptance criteria with the user before writing code
4. Implement each step from the prompt
5. Run the verification commands from the prompt
6. If all criteria pass:
   - Move prompt to `docs/tasks/prompts/complete/`
   - Stage and commit:
     ```bash
     git add -p
     git commit -m "feat: {task name}

     Authored by: Sean @ coin"
     ```
7. Report completion:
   ```
   ✅ {task-id} complete — {n} files changed
   Next: /docs-update {task-id}
   ```

## Rules
- Never skip the verification step
- Never mark complete if any acceptance criterion is untested
- If blocked, keep prompt in pending/ and report what's blocking
