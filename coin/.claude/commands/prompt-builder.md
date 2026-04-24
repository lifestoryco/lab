---
description: Research a task from the roadmap and generate a self-contained prompt file for /run-task.
---

# /prompt-builder [task-id]

**Usage:** `/prompt-builder S-1.2`

Generates a fully-specified task prompt and saves it to `docs/tasks/prompts/pending/`.

---

## Steps

1. Read `docs/roadmap.md` and find the task matching `[task-id]`
2. Read all relevant source files for the task scope
3. Write a self-contained prompt file:

```markdown
# {Task ID} — {Task Name}
**Date:** {YYYY-MM-DD}
**Lane:** {which part of the system}

## Objective
{1 paragraph — what this task accomplishes and why}

## Acceptance Criteria
- [ ] {specific, testable criterion}
- [ ] {specific, testable criterion}

## Context
{Relevant file paths, current state, constraints from CLAUDE.md}

## Implementation Steps
1. {step}
2. {step}

## Verification
```bash
{exact commands to confirm the task is complete}
```
```

4. Save to `docs/tasks/prompts/pending/{task-id}_{MM-DD}_{slug}.md`
5. Report: `✅ Prompt saved: docs/tasks/prompts/pending/{filename}`

## Task naming: S-X.Y
- `S-1.x` — Phase 1: Core pipeline (scraper, analyzer, transformer, pipeline DB)
- `S-2.x` — Phase 2: Resume quality + compensation intelligence
- `S-3.x` — Phase 3: Automation + scheduling + multi-board coverage
