---
task: COIN-AUTOPIPELINE
title: Author modes/auto-pipeline.md — paste JD or URL, get full pipeline run
phase: Modes Build-Out
size: L
depends_on: COIN-AUDIT
created: 2026-04-25
---

# COIN-AUTOPIPELINE: Author `modes/auto-pipeline.md`

## Context

Today the user must run a chain of commands to take a JD from "I just saw this posting" to "submission-ready PDF in hand": `/coin <url>` → wait → `/coin tailor <id>` → `/coin audit <id>` → fix → `/coin pdf <id> --recruiter` → review → `/coin track <id> applied`.

That's 5 manual hops. Friction kills throughput in a job search; a recruiter screen is open for 5–14 days, not 5 weeks.

`auto-pipeline` collapses the chain. Sean pastes a JD or URL with no other directive — Coin runs ingest → score → tailor → audit → render → track → report in one pass, stopping only at the `applied` gate (which requires a real-world commitment).

This is the "killer mode" called out in the synthesized SKILL.md. Until it ships, Coin's UX is just a thin wrapper around individual scripts.

## Goal

Create `modes/auto-pipeline.md` so that `/coin <pasted JD or URL>` (no sub-command) produces a fully tailored, audited, and rendered PDF plus a one-screen summary, with no other prompts to the user except the final `applied` confirmation.

## Pre-conditions

- [ ] `modes/audit.md` exists (COIN-AUDIT must ship first)
- [ ] `scripts/fetch_jd.py`, `scripts/render_pdf.py`, `scripts/discover.py` all work
- [ ] `careerops.score.score_breakdown` returns 8-dimension breakdown
- [ ] `careerops.pipeline` has `upsert_role`, `update_jd_raw`, `update_jd_parsed`, `update_fit_score`, `update_status`, `get_role`
- [ ] DB schema supports the full state machine (currently 11 states per `careerops/pipeline.py`)

## Steps

### Step 1 — Define the trigger conditions

Author `modes/auto-pipeline.md`. The mode file must specify when SKILL.md routes here vs. elsewhere:

**Trigger if the user input matches ANY:**
1. URL starting with `http://` or `https://` AND no other sub-command keyword
2. Multi-line text (3+ newlines) containing 2+ of: "responsibilities", "requirements", "qualifications", "about the role", "what you'll do", "we're looking for", "must have", "preferred"
3. Any input ≥ 800 characters that looks like prose (not a command)

**Do NOT trigger if** the input starts with a known sub-command (`tailor`, `audit`, `track`, `status`, etc.) — those route to their dedicated mode.

### Step 2 — Define the 8-step pipeline

The mode walks the agent through these steps in strict order. Each step has a clear input → output contract.

**Step 2.1 — INGEST**
- If URL: `.venv/bin/python scripts/fetch_jd.py --url '<url>'` → returns JSON with `id`, `company`, `title`, `location`, `jd_raw`, `jd_parsed`
- If JD text: parse the text inline (extract company + title from the first 200 chars or ask Sean to confirm), insert via `careerops.pipeline.upsert_role`, then call `update_jd_raw` with the full text
- Determine lane via `careerops.score.score_title` against all 4 lanes; pick the lane with the highest `score_title` result. If tied, use `careerops.pipeline.update_lane` after asking Sean.

**Step 2.2 — SCORE**
- Run `score_breakdown(role, lane, parsed_jd=parsed)` and `update_fit_score(id, composite)`
- If `lane == "out_of_band"` (FAANG pedigree filter), STOP and report: *"Role <id> at <company> is pedigree-filtered. Targeting it would burn tailoring effort on a likely recruiter-screen reject. Override with `/coin tailor <id> --force` if you really want to."*
- If composite < 50 (D or F), STOP and ask Sean: *"This role scored <X> (<grade>). Tailor anyway? Most D/F roles waste effort."*

**Step 2.3 — TRUTHFULNESS PRE-LOAD**
- Re-read `.claude/skills/coin/references/priority-hierarchy.md` and the `Sean's canonical facts` block in SKILL.md
- This is required before generating any tailored prose — protects against the Cox/TitanX/Fortune-500 inflation pattern caught in the 2026-04-24 code review

**Step 2.4 — TAILOR**
- Execute the `modes/tailor.md` flow (load it inline; do not shell out)
- Output: `data/resumes/generated/<id:04d>_<lane>_<YYYY-MM-DD>.json`
- Update status to `resume_generated`

**Step 2.5 — AUDIT**
- Execute the `modes/audit.md` flow (load it inline)
- If verdict is BLOCK, STOP and present the audit report. Ask Sean: *"Auto-fix the CRITICAL items? (y/n)"*
- If yes, apply fixes, re-audit, re-loop. Max 2 iterations.
- If still BLOCK after 2 iterations, escalate to Sean: *"Manual revision needed. Edit the JSON and run `/coin audit <id>` to verify."*
- If verdict is NEEDS REVISION (HIGH only, no CRITICAL), surface the issues but continue — Sean will see them in the report.

**Step 2.6 — RENDER**
- Run `.venv/bin/python scripts/render_pdf.py --role-id <id> --recruiter`
- Confirm PDF was written; capture file path and size

**Step 2.7 — TRACK**
- Status remains `resume_generated` (already set in 2.4)
- Record audit verdict and any HIGH issues in the role's `notes` field via `update_role_notes`

**Step 2.8 — REPORT**

Print a single-screen summary in this exact shape:

```
═══════════════════════════════════════════════
  Auto-Pipeline — Role <id>
  <company> — <title>
  Lane: <lane>  ·  Fit: <score> (<grade>)  ·  <location>
═══════════════════════════════════════════════

EXECUTIVE SUMMARY
  <first 2 sentences of resume.executive_summary>

TOP 3 BULLETS
  1. <top_bullets[0]>
  2. <top_bullets[1]>
  3. <top_bullets[2]>

GAPS TO PREP
  · <skills_gap[0]>
  · <skills_gap[1]>

AUDIT VERDICT: <CLEAN | NEEDS REVISION | BLOCK>
<if HIGH issues: list them, max 3>

ARTIFACTS
  JSON: data/resumes/generated/<id:04d>_<lane>_<date>.json
  PDF:  data/resumes/generated/<id:04d>_<lane>_<date>_recruiter.pdf

NEXT STEP
  → Review the PDF (`open <path>`)
  → If looks good: /coin track <id> applied  (after you actually submit)
  → If needs edits: /coin audit <id> after manual JSON edits
```

### Step 3 — Define the human gates

Only TWO gates in the auto-pipeline (everything else flows):

| Gate | When | Why |
|---|---|---|
| Audit BLOCK auto-fix | If audit returns BLOCK | Never silently rewrite tailored content — Sean must approve fixes |
| `applied` transition | Always required (separate command) | Real-world commitment — auto-pipeline NEVER auto-submits |

### Step 4 — Wire SKILL.md trigger

The SKILL.md table already lists `auto-pipeline` for "looks like a JD" inputs. Confirm the regex/keyword detection matches Step 1's trigger spec. If not, update SKILL.md's routing table to be explicit about the criteria.

### Step 5 — Add an end-to-end smoke test

Add `tests/test_auto_pipeline.py` that:
1. Inserts a known-good JD text (e.g., a sanitized copy of the Filevine SE posting) into the DB
2. Runs the auto-pipeline logic through Step 2.6 (skip Step 2.7 since `update_role_notes` may not exist yet — add it if needed)
3. Asserts a JSON exists at the expected path
4. Asserts a PDF exists and is > 30KB
5. Asserts the role's status is `resume_generated`
6. Asserts the audit verdict was captured in notes

This is the regression net for the whole pipeline.

### Step 6 — Update SKILL.md menu

The Discovery menu in SKILL.md already says "Just paste a JD or URL → I'll run the full pipeline (auto-pipeline)". Make sure this messaging matches what auto-pipeline actually does after this task.

**HUMAN GATE:** Before running the full pipeline on a real role for the first time, manually verify each individual command works in isolation (`/coin <url>`, `/coin tailor <id>`, `/coin audit <id>`, `/coin pdf <id>`). The auto-pipeline assumes those primitives are healthy.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short

# Manual smoke (needs a fresh role URL)
# /coin https://www.linkedin.com/jobs/view/sales-engineer-at-filevine-4379991176
# Expect: ingest → score → audit (CLEAN or NEEDS REVISION) → render → report
```

- [ ] `modes/auto-pipeline.md` exists, follows the 8-step shape
- [ ] All trigger conditions documented in Step 1
- [ ] All 8 sub-steps have explicit input/output contracts
- [ ] Output report shape matches the spec exactly
- [ ] Two human gates are in place (audit auto-fix, applied)
- [ ] `tests/test_auto_pipeline.py` passes end-to-end
- [ ] Manual smoke produces a recruiter-mode PDF in under 90 seconds

## Definition of Done

- [ ] `modes/auto-pipeline.md` authored
- [ ] Trigger detection works (paste JD → routes here; paste `tailor 5` → routes to tailor)
- [ ] End-to-end smoke test passes
- [ ] Manual run of `/coin <fresh URL>` produces a clean PDF + report
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/auto-pipeline.md tests/test_auto_pipeline.py
# Revert SKILL.md trigger if it was tightened
git checkout .claude/skills/coin/SKILL.md
git checkout docs/state/project-state.md
```

Existing modes (tailor, audit, track, pdf) remain functional standalone.
