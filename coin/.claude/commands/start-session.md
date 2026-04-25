# START SESSION

> **Preamble:** You are orienting the developer for a new work session. Report what happened last, what is next, and whether the environment is healthy. Do not start any work until explicitly told. If you discover a systemic issue during startup (broken symlinks, stale env, missing state file), fix the root cause rather than working around it. Boil the Lake.

## Step 1 — Run the start script

```bash
bash scripts/start.sh "$PWD"
```

If you see `❌`, stop and report the error. Otherwise continue.

## Step 2 — Read context

Read `docs/state/project-state.md` if it exists (CLAUDE.md is already loaded).

## Step 3 — Brief the user

Print ONE concise block:

```
═══════════════════════════════════════════════
  Session: <name> | Branch: claude/<name>
  Base: <hash> | Env: ✅ or ⚠️
═══════════════════════════════════════════════
```

Then if project-state.md exists:
- **Last session:** 2-3 bullets from "What Was Just Done"
- **What's next:** Top 3 items from "What's Next"

**Need env vars?** If the project uses a cloud provider (Vercel, Railway, etc.), remind the user they can refresh env vars now before starting work.

Otherwise, wait for go-ahead.

## Rules

- Do NOT start work until the user gives explicit go-ahead.
- Do NOT modify files outside the worktree.
- Do NOT run type checkers at session start — save for when you write code.
