---
task: COIN-DISQUALIFIERS
title: JD-aware disqualifier scanner — quarantine clearance/ITAR/degree-required, penalize stack mismatches
phase: Scoring Hardening
size: M
depends_on: COIN-AUTOPIPELINE
created: 2026-04-27
---

# COIN-DISQUALIFIERS: JD-aware quarantine + soft-penalty layer

## Context

Today's `/coin discover --utah` produced 40 roles. Title-only scoring let
**4 roles score 72.4** (well above the apply-bar) that Sean had to manually
flag and skip after reading the JDs:

| # | Company | Title | Real disqualifier |
|---|---|---|---|
| 4  | Rock West Composites | Engineering / TPM | "BS or BA degree in an engineering or materials science discipline; OR more than 15 years' experience in development of manufacturing processes of advanced composite materials. Minimum 8 years' experience in a composite manufacturing environment. ... U.S. Person under 22 CFR 120 (due to ITAR Restrictions)" |
| 9  | HPE | Federal Technical Program Manager | Title literally reads "(Clearance Secret Required)" |
| 13 | JourneyTeam | Sales Engineer | Microsoft stack (D365, Power Platform, Azure) — Sean has none of these |
| 14 | Coda Technologies | Sales Engineer | Cybersecurity-deep SE (advise customer security teams) — Sean is not a security specialist |

The signals were **in the JD text** but never read — `score.score_title`
matches lane keywords against the title only and happily returns 72.4 for
"Federal Technical Program Manager" because "Technical Program Manager" is
a perfect mid-market-tpm hit.

**Sean is a US citizen**, so "US person required" / "US citizenship" is
NOT a disqualifier on its own. But **clearance** (Secret/TS/SCI/Public
Trust) and **ITAR** (22 CFR 120/121, "export controlled") ARE — Sean has
no clearance, has never had one, and a clearance pipeline is 6–18 months.
Same with hard CS/engineering degree gates: Sean has BA History + MBA WGU
+ PMP, no engineering degree, and "BS in Materials Science required" is
an automated-resume-screener kill.

Soft signals (Microsoft stack mismatch, narrow security domain) shouldn't
quarantine — Sean might still take a shot — but they should drop the
composite by ~20 points so D365 SE roles don't outrank Filevine SE roles.

This task adds a `disqualifiers` module that runs **after JD fetch**, sets
`lane='out_of_band'` on hard hits, and applies a soft penalty otherwise.
The output also feeds the future audit report and dashboard tooltip
(forward compat with `COIN-WEB-UI`).

## Goal

After `COIN-DISQUALIFIERS` ships, the four roles above are caught
automatically:

- Role 4 (Rock West) → quarantined (`out_of_band`), reasons = `['itar_restricted', 'degree_required']`
- Role 9 (HPE) → quarantined, reasons = `['clearance_required']`
- Role 13 (JourneyTeam) → soft-penalized -20, reason = `msft_stack_mismatch`
- Role 14 (Coda) → soft-penalized -20, reason = `narrow_security_domain`

And no false positives: a JD that says "BS in CS or equivalent experience"
must NOT trigger the hard degree DQ.

## Pre-conditions

- [ ] `careerops.score.score_breakdown` exists with current shape (file at `careerops/score.py:176`)
- [ ] `careerops.pipeline.update_lane` and `careerops.pipeline.update_role_notes` exist
- [ ] `data/resumes/base.py::PROFILE['skills']` is a list of skill strings
- [ ] m004 migration applied (so `out_of_band` quarantine pattern works) — verify with `.venv/bin/python -c "from careerops.pipeline import LANES; print('out_of_band' in LANES)"`
- [ ] Existing test suite is green: `.venv/bin/pytest tests/ -q` passes 228 tests

## Steps

### Step 1 — Author `careerops/disqualifiers.py`

New module. Source-of-truth for all DQ rules. Public API:

```python
from typing import TypedDict
import re

class DqResult(TypedDict):
    hard_dq: list[str]                 # reason codes that quarantine
    soft_dq: list[tuple[str, int]]     # (reason, negative penalty)
    matched_phrases: dict[str, str]    # reason -> original substring (for explainability)


HARD_DQ_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Active US security clearance — Sean has none
    (re.compile(r'\b(secret|top.secret|ts/sci|public trust)\s+clearance', re.I), 'clearance_required'),
    # ITAR / export-controlled — citizenship alone is not enough; ITAR adds 22 CFR audit overhead
    (re.compile(r'\b(ITAR|22\s*CFR\s*120|22\s*CFR\s*121|export\s+controlled)\b', re.I), 'itar_restricted'),
    # Hard CS/engineering degree gate — see Step 1.1 for the equivalence-clause carve-out
    (re.compile(
        r"(BS|Bachelor'?s?|MS|Master'?s?|B\.S\.|M\.S\.)\s+(degree\s+)?(in|of)\s+"
        r"(Computer Science|CS|Software Engineering|Electrical Engineering|"
        r"Mechanical Engineering|Materials Science|Chemical Engineering)\s+(is\s+)?required",
        re.I,
    ), 'degree_required'),
]

# Soft DQs — apply a penalty but do NOT quarantine
SOFT_DQ_PATTERNS: list[tuple[re.Pattern, str, int, callable]] = [
    # callable signature: (jd_text, profile) -> bool — extra gate beyond the regex match
    # Microsoft stack mismatch — only triggers if profile.skills doesn't already contain MSFT terms
    (
        re.compile(r'\b(Microsoft\s+stack|Azure|\.NET|C#|Power\s+Platform|Power\s+BI|Dynamics\s+365|D365)', re.I),
        'msft_stack_mismatch',
        -20,
        lambda jd, profile: not any(s.lower() in {'azure', '.net', 'c#', 'power bi', 'd365', 'dynamics 365', 'power platform'}
                                     for s in profile.get('skills', [])),
    ),
    # Cybersecurity-deep SE — only triggers if 3+ infosec mentions AND title contains 'security'/'cyber'
    (
        re.compile(r'\b(cybersecurity|infosec|SIEM|SOC|threat\s+intel|penetration|red\s+team|blue\s+team|zero\s+trust)\b', re.I),
        'narrow_security_domain',
        -20,
        lambda jd, profile: True,  # frequency + title check happens inside scan_jd
    ),
    # (Future expansion slot — quantum, regulated FinTech, pharma-clinical, healthcare-clinical, etc.)
]
```

#### Step 1.1 — `scan_jd(jd_text: str, profile: dict) -> DqResult`

Logic:

1. Initialize `result = {'hard_dq': [], 'soft_dq': [], 'matched_phrases': {}}`
2. **Hard DQ pass** — for each `(pattern, reason)` in `HARD_DQ_PATTERNS`:
   - Find all matches. If none, skip.
   - **Equivalence carve-out for `degree_required`**: if the matched substring is followed within 30 chars by `or equivalent (experience|work experience)?` (case-insensitive), treat as soft (do not append to `hard_dq`). Use a lookahead window — slice `jd_text[match.end():match.end()+60]` and run a secondary `re.search(r'or equivalent', window, re.I)`. If found, skip the hard DQ (do NOT add to `soft_dq` either — this is intentional; the equivalence clause means Sean's 15 years of experience qualifies).
   - Otherwise append `reason` to `hard_dq` and store `result['matched_phrases'][reason] = match.group(0)`.
3. **Soft DQ pass** — for each `(pattern, reason, penalty, gate)` in `SOFT_DQ_PATTERNS`:
   - For `narrow_security_domain` specifically: count `len(pattern.findall(jd_text))` and require >= 3 AND `re.search(r'\b(security|cyber)\b', profile.get('_target_title', ''), re.I)` is truthy. (The role's title is passed in via `profile['_target_title']` — see Step 1.2 contract.)
   - For other soft rules: regex match + `gate(jd_text, profile)` returning True.
   - If gated, append `(reason, penalty)` to `soft_dq` and record matched_phrases.
4. Return `result`.

#### Step 1.2 — `apply_disqualifiers(role: dict, parsed_jd: dict, profile: dict) -> DqResult`

Mutating helper (callers expect side effects on `role`):

1. Build `enriched_profile = {**profile, '_target_title': role.get('title', '')}` so `scan_jd` can do the security-title check.
2. Call `dq = scan_jd(role.get('jd_raw') or parsed_jd.get('raw', ''), enriched_profile)`.
3. If `dq['hard_dq']`:
   - Set `role['lane'] = 'out_of_band'`
   - Append `f"DQ: {','.join(dq['hard_dq'])}"` to `role['notes']` (preserve existing notes with `\n`)
4. Return `dq`. (Caller is responsible for persisting via `pipeline.update_lane` + `pipeline.update_role_notes`.)

### Step 2 — Extend `careerops/score.py::score_breakdown`

Current signature (per `careerops/score.py:176`) returns a dict with
`composite, grade, dimensions{...}`. Extend:

1. Add optional kwarg `dq_result: DqResult | None = None` (default None preserves backward compat — every existing test continues to pass).
2. **Hard-DQ short circuit** — if `dq_result` and `dq_result['hard_dq']`:
   - Return the existing quarantine shape (composite=0, grade='F', dimensions all zero — match the shape `careerops/score.py` already produces for `lane='out_of_band'`)
   - PLUS two new top-level fields: `'disqualified': True`, `'dq_reasons': dq_result['hard_dq']`
3. **Soft-DQ penalty** — if `dq_result` and `dq_result['soft_dq']` (and no hard hits):
   - Compute `penalty = sum(p for _, p in dq_result['soft_dq'])` (already negative numbers)
   - `composite = max(0, min(100, composite + penalty))`
   - Recompute `grade` from the clamped composite using the existing grade-band helper
   - Add a new informational dimension: `dimensions['domain_fit'] = {'raw': max(0, 100 + penalty), 'weight': 0.0, 'weighted': 0.0}` — weight=0 means it doesn't double-count; the penalty already hit `composite`. The dimension exists purely for dashboard display.
   - Add `'disqualified': False`, `'dq_reasons': [r for r, _ in dq_result['soft_dq']]`
4. **No DQ** — if `dq_result is None` or both lists empty: behave exactly as today (no new keys added — keeps the 228 existing tests untouched).

### Step 3 — Mirror rules into `coin/config.py`

Add two constants near the existing `LANE_KEYWORDS` / `ARCHETYPE_KEYWORDS` blocks:

```python
# Hard disqualifiers — sourced from careerops/disqualifiers.py:HARD_DQ_PATTERNS
# Listed here for editability without touching the regex logic in disqualifiers.py.
DISQUALIFIER_PATTERNS: list[tuple[str, str]] = [
    (r'\b(secret|top.secret|ts/sci|public trust)\s+clearance', 'clearance_required'),
    (r'\b(ITAR|22\s*CFR\s*120|22\s*CFR\s*121|export\s+controlled)\b', 'itar_restricted'),
    (r"(BS|Bachelor'?s?|MS|Master'?s?|B\.S\.|M\.S\.)\s+(degree\s+)?(in|of)\s+(Computer Science|CS|Software Engineering|Electrical Engineering|Mechanical Engineering|Materials Science|Chemical Engineering)\s+(is\s+)?required", 'degree_required'),
]

# Soft penalties — sourced from careerops/disqualifiers.py:SOFT_DQ_PATTERNS
DOMAIN_PENALTY_RULES: list[tuple[str, str, int]] = [
    (r'\b(Microsoft\s+stack|Azure|\.NET|C#|Power\s+Platform|Power\s+BI|Dynamics\s+365|D365)', 'msft_stack_mismatch', -20),
    (r'\b(cybersecurity|infosec|SIEM|SOC|threat\s+intel|penetration|red\s+team|blue\s+team|zero\s+trust)\b', 'narrow_security_domain', -20),
]
```

Keep `disqualifiers.py` as the single source of truth — `config.py` is a
plain restatement for hand-editing. Add a comment in `disqualifiers.py`
that `config.py` must be updated in lockstep.

### Step 4 — Wire into `modes/score.md`

Find Step 3 (post JD-fetch + parse). Insert this block before the
`score_breakdown` call:

```
3a. Run `careerops.disqualifiers.scan_jd(jd_raw, PROFILE)` with the role's title
    passed via `_target_title` (use `apply_disqualifiers(role, parsed, PROFILE)`).

3b. If `dq_result['hard_dq']` is non-empty:
    - Call `careerops.pipeline.update_lane(role_id, 'out_of_band')`
    - Call `careerops.pipeline.update_role_notes(role_id, f"DQ: {','.join(dq_result['hard_dq'])}")`
    - STOP and report:  "Role <id> at <company> hard-DQ'd: <reasons>.
      Quarantined to out_of_band. Override with /coin tailor <id> --force."
    - Do NOT proceed to scoring.

3c. Otherwise, pass `dq_result=dq_result` to `score_breakdown(...)`. The composite will
    already reflect any soft penalties.
```

### Step 5 — Wire into `modes/auto-pipeline.md` Step 2.2 (SCORE)

Same insertion. Locate the existing Step 2.2 SCORE block. Add the same
3a/3b/3c sub-steps before `update_fit_score` is called. The `out_of_band`
short-circuit replaces the existing FAANG-pedigree STOP message — extend
that block to handle the new DQ reasons too:

```
If lane == 'out_of_band' (FAANG pedigree filter OR hard JD disqualifier),
STOP and report: "Role <id> at <company> is quarantined: <dq_reasons or 'pedigree-filtered'>.
Targeting it would burn tailoring effort on a likely auto-reject.
Override with /coin tailor <id> --force if you really want to."
```

### Step 6 — Author `tests/test_disqualifiers.py` (15+ tests)

Use the real JD excerpts as fixtures. Sean pasted the Rock West verbatim;
include it word-for-word so future regex tweaks can't silently regress.

```python
ROCK_WEST_JD = """
Rock West Composites is seeking a Manufacturing Engineer ...
BS or BA degree in an engineering or materials science discipline;
OR more than 15 years' experience in development of manufacturing processes
of advanced composite materials. Minimum 8 years' experience in a composite
manufacturing environment. ...
Must be a U.S. Person under 22 CFR 120 (due to ITAR Restrictions).
"""

HPE_JD = """
Federal Technical Program Manager, (Clearance Secret Required)
Hewlett Packard Enterprise is seeking a TPM to lead federal programs.
Active Secret clearance required. ...
"""

JOURNEYTEAM_JD = """
Sales Engineer — JourneyTeam
You will demo Microsoft Dynamics 365, Power Platform, Power BI, and
Azure-hosted solutions to customers. Hands-on D365 experience required.
"""

CODA_JD = """
Sales Engineer — Coda Technologies
You will advise customer cybersecurity teams on threat intel, SIEM
deployments, SOC workflows, zero trust architecture, and red team /
blue team exercises. Cybersecurity domain expertise required.
"""

EQUIVALENCE_JD = """
We're looking for a software engineer with a BS in Computer Science required,
or equivalent experience. ...
"""
```

Required tests (minimum 15):

1. `test_rockwest_hard_dq_itar_and_degree` — `scan_jd(ROCK_WEST_JD, PROFILE)['hard_dq']` contains both `'itar_restricted'` and `'degree_required'`
2. `test_hpe_hard_dq_clearance` — `scan_jd(HPE_JD, PROFILE)['hard_dq'] == ['clearance_required']`
3. `test_journeyteam_soft_dq_msft_stack` — `scan_jd(JOURNEYTEAM_JD, PROFILE)['soft_dq']` contains `('msft_stack_mismatch', -20)`
4. `test_coda_soft_dq_security` — pass `PROFILE` with `_target_title='Sales Engineer — Coda Technologies'`; assert `('narrow_security_domain', -20)` in soft_dq
5. `test_clearance_variants` — parametrize over `['Secret clearance required', 'TS/SCI clearance', 'Public Trust clearance', 'Top Secret clearance']` — each yields `clearance_required`
6. `test_itar_variants` — parametrize over `['ITAR restrictions', '22 CFR 120', '22 CFR 121', 'export controlled item']` — each yields `itar_restricted`
7. `test_degree_required_hard` — `'BS in Computer Science is required'` → hard_dq contains `degree_required`
8. `test_degree_or_equivalent_not_hard` — `EQUIVALENCE_JD` → `degree_required` is NOT in hard_dq AND NOT in soft_dq (the equivalence clause means Sean's experience qualifies)
9. `test_msft_stack_with_skill_does_not_trigger` — pass profile with `skills=['Azure', 'Power BI']` and JD mentioning Azure → soft_dq is empty
10. `test_msft_stack_without_skill_triggers` — profile `skills=[]`, JD mentioning D365 → soft_dq has `msft_stack_mismatch`
11. `test_security_3_mentions_with_security_title_triggers` — JD with 3+ security terms + `_target_title='Sales Engineer Cybersecurity'` → soft_dq has it
12. `test_security_1_mention_does_not_trigger` — JD with one passing mention of "SIEM" → soft_dq empty
13. `test_security_3_mentions_without_security_title_does_not_trigger` — JD with 3+ terms but `_target_title='Sales Engineer'` (no security/cyber word) → soft_dq empty
14. `test_apply_disqualifiers_mutates_lane_on_hard` — call `apply_disqualifiers({'title': 'TPM', 'jd_raw': HPE_JD, 'lane': 'mid-market-tpm', 'notes': ''}, {}, PROFILE)`; assert role's `lane == 'out_of_band'` and `'DQ: clearance_required'` in notes
15. `test_apply_disqualifiers_does_not_mutate_lane_on_soft` — pass JOURNEYTEAM_JD; assert role's lane unchanged
16. `test_score_breakdown_with_hard_dq_returns_composite_zero` — `score_breakdown(role, lane, dq_result={'hard_dq': ['clearance_required'], 'soft_dq': [], 'matched_phrases': {}})` → `composite == 0`, `grade == 'F'`, `disqualified is True`, `dq_reasons == ['clearance_required']`
17. `test_score_breakdown_with_soft_dq_deducts` — set up a role that would normally score 75; pass `dq_result={'hard_dq': [], 'soft_dq': [('msft_stack_mismatch', -20)], 'matched_phrases': {}}` → `composite == 55`, `dq_reasons == ['msft_stack_mismatch']`, `dimensions['domain_fit']['weight'] == 0`
18. `test_score_breakdown_no_dq_unchanged` — `dq_result=None` → output identical to current behavior (no new keys); use a snapshot of an existing test's expected dict
19. `test_matched_phrases_populated` — `scan_jd(HPE_JD, PROFILE)['matched_phrases']['clearance_required']` contains the literal text `'Secret clearance'` (substring match) — this is for dashboard explainability

### Step 7 — Verify existing test suite is untouched

Run `.venv/bin/pytest tests/ -q --tb=short` and confirm: existing 228
tests still pass + 15+ new tests pass = 243+ green. If any existing
score test fails, the most likely cause is that you added a new key to
the `score_breakdown` return value without gating it behind
`dq_result is not None`. Fix by ensuring the no-DQ path is byte-identical
to today's output.

## Acceptance

- [ ] `careerops/disqualifiers.py` exists with `scan_jd` and `apply_disqualifiers`
- [ ] `careerops/score.py::score_breakdown` accepts `dq_result` kwarg; behavior unchanged when None
- [ ] `coin/config.py` mirrors the rule lists as `DISQUALIFIER_PATTERNS` and `DOMAIN_PENALTY_RULES`
- [ ] `modes/score.md` and `modes/auto-pipeline.md` invoke the scanner before scoring
- [ ] `tests/test_disqualifiers.py` has ≥ 15 tests, all green
- [ ] `.venv/bin/pytest tests/ -q` shows 243+ passed, 0 regressions
- [ ] Manual verification (after `scripts/fetch_jd.py --id 4` runs successfully):
  ```bash
  .venv/bin/python -c "
  from careerops.disqualifiers import scan_jd
  from careerops.pipeline import get_role
  from data.resumes.base import PROFILE
  for rid in (4, 9, 13, 14):
      r = get_role(rid)
      profile = {**PROFILE, '_target_title': r['title']}
      result = scan_jd(r['jd_raw'] or '', profile)
      print(f'role {rid}: hard={result[\"hard_dq\"]} soft={result[\"soft_dq\"]}')
  "
  ```
  Expected output:
  ```
  role 4: hard=['itar_restricted', 'degree_required'] soft=[]
  role 9: hard=['clearance_required'] soft=[]
  role 13: hard=[] soft=[('msft_stack_mismatch', -20)]
  role 14: hard=[] soft=[('narrow_security_domain', -20)]
  ```

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/python -m pytest tests/test_disqualifiers.py -v
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -c "from careerops import disqualifiers, score, pipeline; print('imports OK')"
.venv/bin/pip list | grep -i anthropic || echo "anthropic: absent ✓"
```

## Definition of Done

- [ ] `careerops/disqualifiers.py` authored
- [ ] `careerops/score.py` extended with backward-compatible `dq_result` kwarg
- [ ] `coin/config.py` rule mirrors added
- [ ] `modes/score.md` and `modes/auto-pipeline.md` updated
- [ ] `tests/test_disqualifiers.py` written with 15+ tests, all green
- [ ] Manual 4-role verification produces the expected output above
- [ ] Roles 4, 9, 13, 14 in the live DB are re-scored: 4 + 9 lane = `out_of_band`; 13 + 14 composite drops by 20
- [ ] `docs/state/project-state.md` updated (note new module + the 4 quarantined roles)
- [ ] No regressions in existing `pytest tests/`

## Style notes

- The Rock West JD excerpt **must** be included verbatim in the test
  fixture — Sean pasted it with the exact wording the regex needs to match,
  and any paraphrase risks silent regex regression.
- The "or equivalent experience" carve-out **must** be within 30 chars of
  the degree phrase to count. The intent: a JD that mentions "BS in CS
  required" in one paragraph and "or equivalent experience" three
  paragraphs later is still a hard DQ — those are two different requirements.
  Use a 60-char post-match window (30 chars buffer for the matched degree
  phrase + 30 for the equivalence clause).
- `dq_reasons` and `matched_phrases` are forward-compat with `COIN-WEB-UI`:
  the dashboard tooltip will show "Role quarantined: clearance_required
  (matched: 'Secret clearance')". Don't strip these in any audit-report
  serializer — they're load-bearing for explainability.
- DO NOT add `anthropic` or any LLM SDK to handle DQ detection. Pure
  regex + rule list. Coin runs inside the Claude Code session; this layer
  is deterministic on purpose.

## Rollback

```bash
rm careerops/disqualifiers.py tests/test_disqualifiers.py
git checkout careerops/score.py coin/config.py modes/score.md modes/auto-pipeline.md
git checkout docs/state/project-state.md
# Optionally re-set lanes for roles 4 and 9 if they were already quarantined:
# .venv/bin/python -c "from careerops.pipeline import update_lane; update_lane(4, 'mid-market-tpm'); update_lane(9, 'mid-market-tpm')"
```

Existing scoring + auto-pipeline remain functional with no DQ awareness —
just back to the pre-task behavior where Sean has to read JDs manually.
