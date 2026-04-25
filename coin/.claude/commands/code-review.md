---
description: Multi-agent parallel code review. Four specialist subagents (Security, Logic, Architecture, UX) examine the same code simultaneously and produce independent reports. Use for any change touching auth, data access, or multiple feature areas.
---

# /code-review

Run a multi-agent code review on the current changes.

---

## Phase 1 — Context Gathering

1. Read CLAUDE.md for project rules and non-negotiables
2. Run `git diff` (or `git diff HEAD~N` if reviewing multiple commits) to identify changed files
3. Read each changed file in full to understand context
4. Identify the scope: new feature, bug fix, refactor, etc.

Print scope summary:
```
═══════════════════════════════════════════════
  Review Scope: [N] files | [feature/fix/refactor]
  Mode: [report-only | report + auto-fix]
═══════════════════════════════════════════════
```

---

## Phase 2 — Launch Specialist Reviews

Launch 4 agents in parallel using the Agent tool:

### Security Reviewer (agent: security-reviewer)
- Auth bypasses, injection vulnerabilities, exposed secrets
- API routes missing authentication checks
- OWASP top 10 issues, hardcoded credentials or tokens
- Timing-unsafe comparisons, missing webhook signature verification
- Violations of CLAUDE.md security rules → always CRITICAL

### Architecture Reviewer (agent: code-reviewer)
- N+1 queries, missing database indexes, memory leaks
- DRY violations, unused imports, dead code
- Stale closures in async callbacks
- Pattern consistency with existing codebase
- Type safety violations per CLAUDE.md

### Frontend/UX Reviewer (agent: frontend-engineer)
- Accessibility: ARIA labels, keyboard navigation, WCAG AA contrast
- Responsive: mobile/tablet/desktop breakpoints
- Component patterns: composition, missing loading/error states
- Design system compliance (colors, spacing, touch targets) per CLAUDE.md
- Only review frontend files — if none changed, skip this agent

### Domain Expert (agent: code-reviewer)
- Business logic correctness per CLAUDE.md rules
- Edge cases in data flow, off-by-one errors, null handling
- Missing error handling or incomplete implementations
- Missing audit logging for mutations
- Regression risk

---

## Phase 3 — Synthesize

Merge all findings. Deduplicate. Prioritize:

| Severity | Meaning | Action |
|----------|---------|--------|
| **CRITICAL** | Security hole, data loss, crash | Must fix before merge |
| **HIGH** | Significant bug, broken flow, a11y violation | Should fix soon |
| **MEDIUM** | Performance issue, pattern violation, missing state | Fix in follow-up |
| **LOW** | Style, naming, minor improvement | Nice to fix |

Verdict: **PASS** (0 CRITICAL, 0 HIGH) | **NEEDS ATTENTION** (0 CRITICAL, 1+ HIGH) | **NEEDS WORK** (1+ CRITICAL)

---

## Phase 4 — Report

```
═══════════════════════════════════════════════
  Code Review — [scope] | Verdict: [PASS / NEEDS ATTENTION / NEEDS WORK]
═══════════════════════════════════════════════

WHAT'S GOOD
  [notable positives]

CRITICAL (X) — resolve before merging
  1. [file:line] — description
     Impact: why this matters
     Fix: concrete code or approach

HIGH (X) — resolve soon
  1. [file:line] — description
     Impact: ...  Fix: ...

MEDIUM (X) — address in follow-up
  ...

LOW (X) — informational
  ...

PRE-EXISTING (X) — not introduced by this change
  ...

Approved by: Security, Architecture, UX, Domain
═══════════════════════════════════════════════
```

---

## Phase 5 — Auto-Fix (if `--fix` in $ARGUMENTS)

**HUMAN GATE:** Present all CRITICAL and HIGH findings. Ask: "Fix these automatically?"

If approved:
1. Fix CRITICAL issues first, then HIGH
2. Skip MEDIUM, LOW, and PRE-EXISTING
3. Run type checker after fixes
4. Show diff of changes made

`--fix` does NOT apply to security architecture changes or public API changes without explicit confirmation.

---

## Phase 6 — Quality Gate

```bash
npx tsc --noEmit   # TypeScript
# mypy .           # Python
# cargo check      # Rust
# go vet ./...     # Go
```

```
═══════════════════════════════════════════════
  Quality Gate: [PASS | FAIL — N errors]
═══════════════════════════════════════════════
```

## Rules
- Read CLAUDE.md before reviewing — project rules are non-negotiable, violations = CRITICAL
- Cite specific file:line for every finding
- Every finding needs a concrete fix — not just "this is bad"
- Don't flag style preferences — only real issues
- Mark pre-existing issues separately — don't penalize new changes for old debt
- If nothing changed and no files specified: "Nothing to review." and stop
