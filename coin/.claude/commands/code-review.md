---
description: 4-agent parallel code review — Security, Logic, Architecture, and UX agents each review the codebase. High token cost — use before shipping, not on every change.
---

# /code-review

Launch 4 parallel specialist agents. Each reviews the full diff since last commit
(or the entire codebase if no prior commit). Consolidate into one report.

**Usage:** `/code-review` or `/code-review --fix` (auto-fix flagged issues)

---

## Agents

### Agent 1 — Security
Focus: API key exposure, SQL injection, prompt injection via JD content, unsafe subprocess calls, secrets in logs.
Pay special attention to: scraped content passed to Claude prompts (sanitize), SQLite parameterization.

### Agent 2 — Logic
Focus: resume transformer accuracy (does output actually reflect the target lane?), compensation filter threshold enforcement, DB schema consistency, scraper anti-detection correctness.

### Agent 3 — Architecture
Focus: module boundaries (scraper should not call Claude directly — only analyzer/transformer should), config vs. hardcoded values, SQLite connection lifecycle, error propagation patterns.

### Agent 4 — UX/Output
Focus: rich terminal output quality, output card consistency with holo's Bloomberg-style aesthetic, error messages (are they actionable?), command discoverability.

---

## Output format

```
═══════════════════════════════════════════════
  Coin Code Review — {date}
═══════════════════════════════════════════════

🔴 CRITICAL (fix before next push)
  [Security] {issue} — {file:line}

🟡 WARNINGS (fix this session)
  [Logic] {issue} — {file:line}

🟢 SUGGESTIONS (optional)
  [Arch] {issue}

Overall: {PASS / NEEDS WORK}
```

If `--fix` flag: implement all 🔴 and 🟡 items immediately, then re-run verification.
