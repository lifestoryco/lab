# END SESSION

> **Preamble:** You are closing a work session. The quality of this handoff determines the quality of the next session. Every commit must pass the type checker. The state doc must reflect reality, not aspiration. If you introduced a workaround during this session, document the real fix needed in What's Next. Boil the Lake.

Execute in order. No commentary between steps.

---

## Step 1 — Verify + commit all changes

Run your project's type checker (e.g., `npx tsc --noEmit`). If there are NEW errors you introduced, fix them. Pre-existing errors are acceptable.

Then `git status`. If uncommitted changes exist:
- Stage and commit with appropriate prefix
- Prefixes: `feat:` · `fix:` · `refactor:` · `docs:` · `test:` · `chore:`
- One commit per logical change. Don't batch unrelated work.

---

## Step 2 — Update project state

If `docs/state/project-state.md` exists, update these sections:

**Header:** `_Last updated: YYYY-MM-DD | Session: <name> — <1-line description>_`

**Current Status:** Update build status, active tasks, blockers in-place (replace, don't append).

**What Was Just Done:** Insert a NEW block above the old one:
```markdown
## What Was Just Done (YYYY-MM-DD — Session: <name>)
### <Task/Feature> ✅ COMPLETE  ← or 🚧 IN PROGRESS / ⏸ BLOCKED
**New files:** `path` — purpose
**Modified:** `path` — what changed
**Commits:** `hash` — message
**Decisions:** Decision → Rationale (if any)
```

**What's Next:** Re-rank top 5. Remove completed items. Add new blockers.

**Previous Sessions:** Summarize old "What Was Just Done" entries to 2-3 lines and move to Previous Sessions. Keep max 4 full sessions visible.

Commit: `docs: update session state for <name>`

---

## Step 3 — Update memory (if project has one)

If your project uses a persistent memory system (e.g., `~/.claude/projects/<project>/memory/`), add any **non-obvious learnings** from this session:
- New gotchas discovered
- Confirmed patterns that weren't documented
- "Don't do X" lessons

Skip if nothing new was learned. Don't duplicate what's already in CLAUDE.md.

---

## Step 4 — Run the end script

```bash
bash scripts/end.sh "$PWD"
```

The script validates clean tree, summarizes commits, rebases onto origin/main, pushes, and handles cleanup.

If it fails, report the exact error. Do not attempt manual workarounds.

---

## Step 5 — Final report

```
═══════════════════════════════════════════════
  Session Complete: <name>
  Commits: <n>  |  Main: <hash>  |  Pushed: ✅
═══════════════════════════════════════════════

What was done:
• bullet 1
• bullet 2

What's next:
1. Top priority
2. Second
3. Third
```

## Rules
- Do NOT skip the state file update if it exists — the next session depends on it
- Do NOT use `--force` push
- Do NOT modify files outside the worktree
- If `end.sh` fails, report the error — don't work around it
