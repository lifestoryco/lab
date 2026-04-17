---
description: Close a holo work session cleanly. Verifies changes, runs tests, updates project state, pushes to origin. The quality of this handoff determines the quality of the next session.
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
Pre-existing failures (from before this session started) are acceptable — document them.

Then check git status:
```bash
git status --short
```

If uncommitted changes exist, stage and commit with appropriate prefix:
- `feat:` — new feature or capability
- `fix:` — bug fix
- `refactor:` — restructuring without behavior change
- `docs:` — documentation only
- `test:` — test additions/changes only
- `chore:` — dependency, config, tooling changes

One commit per logical change. Don't batch unrelated work in one commit.

---

## Step 2 — Update project state

Update `docs/state/project-state.md`:

**At the top of the file**, insert a new "What Was Just Done" block:
```markdown
## What Was Just Done ({YYYY-MM-DD})

### {Task or feature name} ✅ COMPLETE  ← or 🚧 IN PROGRESS / ⏸ BLOCKED

**New files:** `path` — purpose  
**Modified:** `path` — what changed  
**Commits:** `{short hash}` — message  
**Decisions:** {Decision → Rationale, if any significant choices were made}
```

**Update in-place** (replace, don't append):
- **Active Blockers** — remove resolved blockers, add new ones discovered
- **Roadmap table** — mark completed tasks ✅, update status of in-progress tasks
- **Resolved Bugs** — add any bugs fixed this session with the date

**Condense old sessions:**
If there are more than 4 full "What Was Just Done" blocks, summarize the oldest ones
to 2-3 bullet points under a `## Previous Sessions` section.

Commit:
```bash
git add docs/state/project-state.md
git commit -m "docs: update project state after {session description}"
```

---

## Step 3 — Check advisory board action items

If there are open action items from `docs/advisory-board/meetings/`, note which ones
were completed this session so the next meeting has accurate continuity.
No file changes needed — just mention it in the session summary.

---

## Step 4 — Run the end script

```bash
bash scripts/end.sh "$PWD"
```

This validates the working tree is clean, then pushes to origin/main.

If it prints `⚠️ Uncommitted changes`, you missed something in Step 1 — go back and commit.
If it prints `❌`, report the exact error. Do not attempt manual workarounds.

---

## Step 5 — Final report

```
═══════════════════════════════════════════════
  Session Complete
  Commits: {n}  |  HEAD: {short hash}  |  Pushed: ✅
═══════════════════════════════════════════════

What was done:
  • {bullet}
  • {bullet}
  • {bullet}

What's next:
  1. {top priority from updated roadmap}
  2. {second}
  3. {third}

Open tasks in pending/:
  {list docs/tasks/prompts/pending/ or "None"}
```

## Rules

- Do NOT skip the state file update — the next session and next board meeting depend on it
- Do NOT force-push
- Do NOT modify files outside the holo directory
- If the test suite has new failures, fix them before pushing — never push broken tests
- If `end.sh` fails, report the error — don't manually push to work around it
- Workarounds introduced during the session MUST be documented in What's Next as real fix items
