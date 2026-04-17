---
description: Orient for a new holo work session. Checks environment health, reads project state, briefs you on what happened last and what's next. Does NOT start work — waits for go-ahead.
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
- Missing venv → run `/holo-setup`
- Missing packages → `.venv/bin/pip install -r requirements.txt`
- Missing config.py → something is very wrong, check git status

## Step 2 — Read context

Read `docs/state/project-state.md` in full.

Also check for any pending advisory board action items:
```bash
ls docs/advisory-board/meetings/ | tail -1
```
Read the most recent meeting file and note any open action items.

## Step 3 — Brief the user

Print ONE concise block:

```
═══════════════════════════════════════════════
  Holo | Branch: {branch}
  HEAD: {short hash} | Env: ✅
═══════════════════════════════════════════════

Last session:
  • {bullet from What Was Just Done}
  • {bullet}
  • {bullet}

What's next:
  1. {top roadmap item}
  2. {second}
  3. {third}

Pending tasks:
  {list files in docs/tasks/prompts/pending/ or "None"}

Open board action items:
  {from most recent meeting, or "None"}
```

**Need env vars?** If working on the web platform (HoloPage.tsx, api/index.py on Vercel),
remind the user to verify `HOLO_API_ORIGIN` is set in their Vercel environment.

Then: **wait for explicit go-ahead before starting any work.**

## Rules

- Do NOT start work until the user gives explicit go-ahead
- Do NOT modify files
- Do NOT run the test suite at session start — save for when code changes
- If `docs/state/project-state.md` is missing, note it and suggest running `/end-session`
  from the previous session to create it
