---
description: Mark tasks done, move prompts to complete/, update roadmap after /run-task finishes.
---

# /docs-update [task-id]

**Usage:** `/docs-update S-1.2`

Run after `/run-task` completes successfully.

---

## Steps

1. Move prompt file from `pending/` to `complete/`:
   ```bash
   mv docs/tasks/prompts/pending/{task-id}_*.md docs/tasks/prompts/complete/
   ```

2. Update `docs/roadmap.md`:
   - Mark the task row as `✅ Done`
   - Set completion date

3. Update `docs/state/project-state.md`:
   - Add to "What Was Just Done"
   - Update Roadmap table status

4. Commit:
   ```bash
   git add docs/
   git commit -m "docs: mark {task-id} complete, update roadmap

   Authored by: Sean @ coin"
   ```

5. Print:
   ```
   ✅ Docs updated for {task-id}
   Pending tasks: {count remaining in pending/}
   ```
