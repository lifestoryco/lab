---
description: Orient for a new Coin work session. Checks environment health, reads project state, briefs you on what happened last and what's next. Does NOT start work — waits for go-ahead.
---

# /start-session

Environment health check + session brief. Run this at the start of every work session.

---

## Step 1 — Run the start script

```bash
bash scripts/start.sh "$PWD"
```

If any `❌` appears, stop and report the error. Do NOT continue past a broken environment.
Common fixes:
- Missing venv → `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Missing packages → `.venv/bin/pip install -r requirements.txt`
- No `.env` is OK — Coin runs without one (`.env` only overrides comp floors and location)
- Coin does NOT need `ANTHROPIC_API_KEY` — all LLM reasoning runs in the host Claude Code session

## Step 2 — Read context

Read `docs/state/project-state.md` in full.

## Step 3 — Brief the user

Print ONE concise block:

```
═══════════════════════════════════════════════
  Coin | Branch: {branch}
  HEAD: {short hash} | Env: ✅
═══════════════════════════════════════════════

Last session:
  • {bullet from What Was Just Done}
  • {bullet}

What's next:
  1. {top roadmap item}
  2. {second}
  3. {third}

Pending tasks:
  {list files in docs/tasks/prompts/pending/ or "None"}

Pipeline status:
  {run: .venv/bin/python -c "from careerops.pipeline import summary; print(summary())" or "DB not initialized"}
```

Then: **wait for explicit go-ahead before starting any work.**

## Rules

- Do NOT start work until the user gives explicit go-ahead
- Do NOT modify files
- If `docs/state/project-state.md` is missing, note it and suggest running `/end-session`
