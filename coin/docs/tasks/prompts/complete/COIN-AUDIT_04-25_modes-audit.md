---
task: COIN-AUDIT
title: Author modes/audit.md — truthfulness check on tailored resume JSON
phase: Modes Build-Out
size: M
depends_on: none
created: 2026-04-25
---

# COIN-AUDIT: Author `modes/audit.md`

## Context

The 2026-04-24 code review found 3 CRITICAL truthfulness issues in the Filevine SE tailored resume (id 137):
- "Personally led pre-sales discovery and stakeholder demos for Cox" — Sean was an agency PM, not the SE
- "Technical credibility on seven-figure circuit deployments for Fortune 500 clients" — unverified inflation
- Header conflict: "Senior Technical Program Manager" vs summary's "Sales Engineer / Solutions Architect"

Plus 4 HIGH issues including "aerospace OEM in-flight wireless" name-dropping, TitanX Series A causation, and Safeguard Global suspiciously-precise metrics.

These slipped past because tailoring runs straight to PDF render with no truthfulness pause. The `audit` mode is the gate.

## Goal

Create `modes/audit.md` so that `/coin audit <id>` reads the tailored JSON for role `<id>`, cross-checks every claim against `data/resumes/base.py` PROFILE, the JD, and the canonical-facts list in `.claude/skills/coin/SKILL.md`, then either reports CLEAN or returns a list of specific issues with fix suggestions. Auto-pipeline mode will call this between `tailor` and `pdf`.

## Pre-conditions

- [ ] `.venv/bin/python` exists at coin root
- [ ] `data/db/pipeline.db` exists with at least one role having `status=resume_generated`
- [ ] `.claude/skills/coin/references/priority-hierarchy.md` exists (provides the rule order)
- [ ] `.claude/skills/coin/SKILL.md` "Sean's canonical facts" section exists

## Steps

### Step 1 — Read the inputs

Author the mode file at `modes/audit.md`. The mode must, when loaded, instruct the agent to read in this exact order:

1. `.claude/skills/coin/references/priority-hierarchy.md` — rule precedence
2. `.claude/skills/coin/SKILL.md` — extract the "Sean's canonical facts" block
3. `data/resumes/base.py` — extract PROFILE positions, education, certifications, skills_grid
4. `config/profile.yml` — extract identity + archetype north_stars
5. `data/resumes/generated/<id:04d>_*.json` (most recent) — the artifact under audit
6. The role's `jd_raw` and `jd_parsed` from the DB

### Step 2 — Define the 9 audit checks

Each check returns PASS / FAIL / WARN with a specific quote of the offending text. The mode file must enumerate and instruct the agent to run each check in order.

| # | Check | Fail condition |
|---|---|---|
| 1 | **Education truthfulness** | `executive_summary` or any bullet claims a CS, EE, or engineering degree |
| 2 | **Pedigree non-claim** | Bullet claims employment AT a FAANG/big-tech company unless backed by a PROFILE.positions entry |
| 3 | **Cox / TitanX / Safeguard attribution** | Any bullet attributes Cox revenue, TitanX Series A, or Safeguard delivery to Sean's personal action without "as Hydrant's <role>" framing |
| 4 | **Vague-flex qualifiers** | Strings "Fortune 500", "seven-figure", "world-class", "industry-leading" appear without a named verifiable account |
| 5 | **Metric provenance** | Every numeric metric in `top_bullets` traces back to a PROFILE.positions[*].bullets entry OR a metric in PROFILE.stories. Invented numbers fail. |
| 6 | **Causation hedging** | "Enabled $X raise", "drove acquisition", "caused growth" claims for outcomes Sean didn't solely produce — must use "during the period", "served as", "owned my book during" |
| 7 | **Header / summary congruence** | If JSON includes `target_role`, it must align with the lane's archetype label. If not, recommend setting `target_role` so the PDF header matches the summary positioning |
| 8 | **JD ↔ skills_gap honesty** | Any required skill in JD that's NOT in PROFILE["skills"] must appear in `skills_gap`. Hiding a known gap fails. |
| 9 | **Domain overreach** | Skills_grid includes "Aerospace & Defense" or similar — flag if Sean has < 2 years' direct delivery in that domain (CA Engineering tenure check via PROFILE.positions[0].start) |

### Step 3 — Define the output format

The mode file must specify the audit report shape:

```
═══════════════════════════════════════════════
  AUDIT — Role <id>: <company> — <title>
  JSON: <path>
  Verdict: CLEAN | NEEDS REVISION | BLOCK
═══════════════════════════════════════════════

CRITICAL (block submission):
  ✗ Check 3 — Cox attribution
    Quote: "Personally led pre-sales discovery and stakeholder demos for Cox"
    Why:   Sean was Hydrant's TPM on the Cox account, not their SE.
    Fix:   "Led program execution for Cox Communications' True Local Labs as
           Hydrant's TPM, partnering with Cox stakeholders through delivery
           to $1M Year 1 revenue."

HIGH:
  ✗ Check 4 — Vague-flex qualifier
    Quote: "...for Fortune 500 clients"
    Why:   No named account verifies "Fortune 500" framing.
    Fix:   Drop the qualifier or name the actual accounts.

PASSED (8 of 9 checks):
  ✓ Check 1 (education) ✓ Check 2 (pedigree) ✓ Check 5 (metrics)
  ✓ Check 6 (causation) ✓ Check 7 (congruence) ✓ Check 8 (gap honesty)
  ✓ Check 9 (domain) ✓ Check 2 (pedigree)

Verdict: BLOCK — fix CRITICAL items before /coin pdf <id>.
```

Verdict rules:
- CLEAN = 0 CRITICAL, 0 HIGH
- NEEDS REVISION = 0 CRITICAL, 1+ HIGH
- BLOCK = 1+ CRITICAL

### Step 4 — Define the auto-fix offer

After printing the report, if there are issues, prompt:
> "Apply suggested fixes to the JSON now? (y/n) — n to manually edit"

If yes, mode rewrites the JSON in place with the suggested fixes, then re-runs the 9 checks. If still not CLEAN, escalate to Sean.

### Step 5 — Wire the mode into SKILL.md

The mode is already routed in `SKILL.md`'s mode table (`audit <id>` → `modes/audit.md`). Confirm the routing line is correct after authoring.

**HUMAN GATE:** Before any auto-fix writes the JSON, show Sean the diff and require explicit "yes" — never silently rewrite a tailored artifact.

### Step 6 — Add a smoke test

Add a pytest at `tests/test_audit_mode.py` that:
1. Reads `data/resumes/generated/0137_enterprise-sales-engineer_2026-04-24.json`
2. Asserts the audit logic catches at least 3 CRITICAL findings (Cox attribution, Fortune 500 qualifier, header conflict)
3. Asserts a hand-crafted CLEAN JSON passes all 9 checks

This test prevents regression — if anyone weakens the audit checks, the test fails.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
# Smoke: load the mode file and verify it parses as well-formed markdown
from pathlib import Path
content = Path('modes/audit.md').read_text()
assert 'Step 1' in content and 'Check 1' in content and 'BLOCK' in content
print('audit.md structure OK')
"
```

- [ ] `modes/audit.md` exists, follows the same shape as `modes/tailor.md`
- [ ] All 9 checks documented with fail conditions
- [ ] Output format spec'd with example
- [ ] Auto-fix flow includes human gate
- [ ] `tests/test_audit_mode.py` passes
- [ ] No regressions in existing `pytest tests/`

## Definition of Done

- [ ] `modes/audit.md` authored
- [ ] Smoke test passes against the known-bad Filevine JSON
- [ ] `docs/state/project-state.md` updated with new mode
- [ ] `/coin audit 137` produces a BLOCK verdict listing the 3 CRITICAL issues from the code review

## Rollback

```bash
rm modes/audit.md tests/test_audit_mode.py
git checkout docs/state/project-state.md
```

The SKILL.md routing line for `audit` was added in the prior session; leaving it intact even without the mode file is a no-op (router will say "mode file missing").
