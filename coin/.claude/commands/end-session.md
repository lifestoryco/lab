---
description: Close a Coin work session cleanly. Verifies changes, runs tests, updates project state, pushes to origin.
---

# /end-session

Close the session. Every step in order. No commentary between steps.

---

## Step 1 — Verify + commit all changes

Run the test suite:
```bash
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -20
```

If there are test failures you introduced this session, fix them before continuing.
Pre-existing failures are acceptable — document them.

Check git status:
```bash
git status --short
```

Commit any uncommitted changes:
- `feat:` new feature or capability
- `fix:` bug fix
- `refactor:` restructuring without behavior change
- `docs:` documentation only
- `test:` test additions/changes only
- `chore:` dependency, config, tooling changes

---

## Step 2 — Update project state

Update `docs/state/project-state.md`. At the top insert:

```markdown
## What Was Just Done ({YYYY-MM-DD})

### {Task name} ✅ COMPLETE  ← or 🚧 IN PROGRESS / ⏸ BLOCKED

**New files:** `path` — purpose
**Modified:** `path` — what changed
**Commits:** `{short hash}` — message
**Decisions:** {Decision → Rationale}
```

Update in-place:
- **Active Blockers** — remove resolved, add new
- **Roadmap table** — mark completed ✅
- **Resolved Bugs** — add any bugs fixed this session

Commit the state update:
```bash
git add docs/state/project-state.md
git commit -m "docs: update project state after {session description}

Authored by: Sean @ coin"
```

---

## Step 3 — Run the end script

```bash
bash scripts/end.sh "$PWD"
```

If `⚠️ Uncommitted changes` appears, go back to Step 1.
If `❌` appears, report the exact error.

---

## Step 4 — Final report

```
═══════════════════════════════════════════════
  Session Complete
  Commits: {n}  |  HEAD: {short hash}  |  Pushed: ✅
═══════════════════════════════════════════════

What was done:
  • {bullet}

What's next:
  1. {top priority from updated roadmap}
  2. {second}
```

## Rules

- Do NOT skip the state file update
- Do NOT force-push
- Do NOT commit `data/db/pipeline.db` or `.env`
- Fix new test failures before pushing — never push broken tests
