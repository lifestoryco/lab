# PROMPT BUILDER — Task Prompt Generator

> **Preamble:** You are generating a self-contained session prompt that another Claude instance will execute autonomously. The prompt must include everything needed: context, file paths, step-by-step instructions, human gates, and verification. A vague prompt produces vague results. Invest in research now so execution is fast and correct later.

Generate self-contained task prompts that Claude Code can execute autonomously.

**Input:** `$ARGUMENTS` — task description or task ID to build a prompt for.

---

## GATE 0 — Parse Request

Extract:
- Task ID (if referencing flight plan): `TASK-X.Y`
- Description of what needs to be done
- Any constraints or dependencies mentioned

If vague, ask one clarifying question. Don't over-ask.

---

## Phase 1 — Research (parallel)

Launch 2 agents:

### Explore Agent (subagent_type: Explore)
- Find all files relevant to the task
- Understand current implementation state
- Identify patterns to follow
- Map dependencies and integration points

### Plan Agent (subagent_type: Plan)
- Design the implementation approach
- Identify risks and edge cases
- Estimate scope (S/M/L/XL)
- Define verification criteria

---

## Phase 2 — Web Research (optional)

If the task involves unfamiliar technology or best practices, use WebSearch to gather:
- Current best practices
- Common pitfalls
- Reference implementations

---

## GATE 1 — Research Review

Present research findings to the user:
```
Research complete. Here's what I found:
- [Key findings from Explore]
- [Approach from Plan]
- [Web research if any]

Proceed with prompt generation? Any adjustments?
```

Wait for approval.

---

## Phase 3 — Assemble Prompt

Write a self-contained task prompt using the template:

```markdown
---
task: TASK-X.Y
title: [Title]
phase: [Phase]
size: [S/M/L/XL]
depends_on: [dependencies]
created: YYYY-MM-DD
---

# TASK-X.Y: [Title]

## Context
[Why this task exists, what it unblocks]

## Goal
[What "done" looks like — one sentence]

## Steps

### Step 1 — [Name]
[Detailed instructions with specific file paths and patterns to follow]

### Step 2 — [Name]
[Instructions]

**HUMAN GATE:** Confirm before proceeding.

### Step 3 — [Name]
[Instructions]

## Verification
- [ ] Type checker passes
- [ ] Build passes
- [ ] [Feature-specific verification]

## Definition of Done
- [ ] All steps completed
- [ ] Verification passes
- [ ] No regressions

## Rollback
[How to revert if something goes wrong]
```

---

## GATE 2 — Draft Review

Present the prompt. Ask:
```
approve → Save to docs/tasks/pending/
revise  → Specific feedback
```

---

## Phase 4 — Save

Save to `docs/tasks/pending/TASK-X-Y_{YYYY-MM-DD}_{slug}.md`

Confirm: `✅ Prompt saved. Run /run-task TASK-X.Y to execute.`

## Rules
- Prompts must be SELF-CONTAINED — everything needed to execute
- Include specific file paths discovered during research
- Include human gates for risky or irreversible steps
- Include rollback instructions
- Each step should be verifiable independently
