---
description: Generate a self-contained holo task prompt that /run-task can execute autonomously. Researches the codebase, designs the implementation, gets your approval, then saves to docs/tasks/prompts/pending/.
---

# /prompt-builder

Generate self-contained task prompts that `/run-task` can execute without follow-up questions.

**Input:** `$ARGUMENTS` — Task ID or description. Examples:
- `H-1.2` — Telegram bot interface
- `H-1.3` — Tournament meta-shift signal (Limitless TCG)
- `H-2.0` — Auth layer and personalization

---

## Gate 0 — Parse Request

Extract:
- Task ID (if referencing the roadmap): `H-X.Y`
- Description of what needs to be done
- Any constraints or dependencies mentioned

Cross-reference with `docs/state/project-state.md` roadmap to confirm the task exists.

If the request is vague about scope, ask ONE clarifying question. Don't over-ask.

---

## Phase 1 — Research (parallel agents)

Launch 2 agents simultaneously:

### Explore Agent
- Find all files relevant to the task in `api/index.py`, `pokequant/`, `config.py`,
  `tests/`, `handoffpack-www/components/lab/holo/`, `vercel.json`
- Understand current implementation state — what exists, what's missing
- Identify patterns to follow (naming conventions, error handling style, test structure)
- Map dependencies: what does this task touch, what does it unblock?

### Plan Agent
- Design the implementation approach for a Python/Vercel/Next.js stack
- Identify risks: scraper fragility, Vercel serverless constraints, SQLite /tmp limitation
- Estimate scope: S (< 2h) / M (2-4h) / L (4-8h) / XL (multi-session)
- Define verification criteria: what does "done" look like for this specific task?

---

## Phase 2 — Web Research (when needed)

If the task involves an unfamiliar API or pattern, WebSearch for:
- Relevant API docs (e.g., Limitless TCG API, Telegram Bot API)
- Current best practices for the technology
- Known pitfalls or rate limits to document in the prompt

---

## Gate 1 — Research Review

Present research findings:

```
Research complete. Here's what I found:

Relevant files:
  • {file: purpose}
  • ...

Implementation approach:
  {Plan agent's recommended approach}

Risks:
  • {risk and mitigation}

Scope estimate: {S/M/L/XL} — ~{N} hours

Web research:
  {Key findings if any}

Proceed with prompt generation? Any adjustments?
```

Wait for approval before writing the prompt.

---

## Phase 3 — Assemble Prompt

Write a self-contained task prompt using this template:

```markdown
---
task: H-X.Y
title: {Title}
phase: {Phase name from roadmap}
size: {S/M/L/XL}
depends_on: {H-X.Y or "none"}
created: {YYYY-MM-DD}
---

# H-X.Y: {Title}

## Context
{Why this task exists, what it unblocks in the H-1.x roadmap}

## Goal
{What "done" looks like — one sentence}

## Pre-conditions
- [ ] {Dependency or prerequisite}
- [ ] venv active and dependencies installed

## Steps

### Step 1 — {Name}
{Detailed instructions with specific file paths and the exact patterns to follow.
Reference line numbers or function names from the research phase.}

### Step 2 — {Name}
{Instructions}

**HUMAN GATE:** {What to confirm before proceeding — e.g., "Confirm the API
response shape looks correct before wiring into the frontend."}

### Step 3 — {Name}
{Instructions}

## Verification

```bash
# Run tests
.venv/bin/pytest tests/ -q --tb=short

# Smoke test the specific feature
{exact command to manually verify it works}
```

- [ ] Test suite passes (no regressions)
- [ ] {Feature-specific check}
- [ ] {Feature-specific check}

## Definition of Done
- [ ] All steps completed
- [ ] Verification passes
- [ ] `docs/state/project-state.md` updated

## Rollback
{Exact commands to revert: git revert, which files to restore, what to re-disable}
```

---

## Gate 2 — Draft Review

Present the full prompt. Ask:
```
approve → Save to docs/tasks/prompts/pending/
revise  → Tell me what to change
```

Wait for one of those responses.

---

## Phase 4 — Save

Save to:
```
docs/tasks/prompts/pending/H-X-Y_{MM-DD}_{slug}.md
```
Where:
- `H-X-Y` uses hyphens (e.g., `H-1-2`)
- `{MM-DD}` is today's date (e.g., `04-16`)
- `{slug}` is 4-6 lowercase hyphenated words from the title

Example: `docs/tasks/prompts/pending/H-1-2_04-16_telegram-bot-interface.md`

Confirm:
```
✅ Prompt saved: docs/tasks/prompts/pending/{filename}
   Run /run-task H-X.Y to execute.
```

## Rules

- Prompts must be SELF-CONTAINED — another Claude instance must be able to execute
  without reading this conversation or asking any questions
- Include specific file paths discovered during research (not "find the relevant file")
- Include HUMAN GATES before any irreversible actions (db schema changes, API credential setup)
- Include rollback instructions
- Vercel serverless constraints must be in any task that touches api/index.py:
  - /tmp only for writes
  - No module-level heavy imports (pandas etc. inside handler functions)
  - 60s max execution time
