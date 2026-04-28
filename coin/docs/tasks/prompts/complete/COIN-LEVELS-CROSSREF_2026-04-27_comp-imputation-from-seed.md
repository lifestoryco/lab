---
task: COIN-LEVELS-CROSSREF
title: Comp imputation from a curated Levels.fyi seed file
phase: Scoring Quality
size: L
depends_on: COIN-AUTOPIPELINE
created: 2026-04-27
---

# COIN-LEVELS-CROSSREF: Impute comp for known companies from a Levels.fyi seed

## Context

Today's discovery returned 40 roles. ALL of them landed in the DB with
`comp_source='unverified'` because LinkedIn's guest endpoint rarely
exposes a comp band, and Indeed is Cloudflare-blocked. The score formula
in `careerops/score.py::score_comp` penalizes that — unverified comp is
hard-coded to 55/100, dragging composite scores into the C/D range even
when the company is known to pay well.

For the long tail (one-off startups, nameless agencies) that penalty is
correct: we genuinely do not know. But for ~50 companies that are
either Utah-relevant (Filevine, Awardco, Weave, MasterControl,
Pluralsight, Lucid, Podium, Recursion, Domo) or marquee remote employers
Sean is targeting (Stripe, Cloudflare, Datadog, Hashicorp, Anthropic,
OpenAI), we have *very good* public signal via Levels.fyi. The penalty
is unfair and demotes real opportunities below noise.

Scraping Levels.fyi at runtime is a TOS gray area, brittle to UI churn,
and overkill — we only need ~50 companies, refreshed quarterly. The
right primitive is a **manually-curated seed file** (`data/levels_seed.yml`)
that the scoring + pipeline layers consult to impute a comp band when
the role's source comp is missing. A future `/coin levels-refresh` mode
(v2.1) will walk Sean through stale entries quarterly; for now the data
structure must support it but the mode itself is a stub.

This task ships the seed, the lookup module, the scoring integration,
the pipeline auto-impute hook, the stub mode, and the test net.

## Goal

After this lands:

1. `data/levels_seed.yml` exists with comp bands for the top ~50
   Utah-relevant + remote-target companies, sourced from Levels.fyi.
2. `careerops/levels.py` provides `load_levels_seed`, `lookup_company`,
   `impute_comp`, `get_seed_age`, and `flag_stale`.
3. `careerops/score.py::score_comp` honors `comp_source='imputed_levels'`
   with a confidence haircut (P50-with-level → 85%; P50-only → 75%).
4. `careerops/pipeline.py::upsert_role` auto-imputes whenever a freshly
   inserted role has `comp_source='unverified'` AND the company is in
   the seed.
5. `modes/levels-refresh.md` documents the quarterly refresh workflow
   (skeletal stub — agent walks Sean through it via file edits in v2.1).
6. SKILL.md routes `/coin levels-refresh` to the new mode.
7. Test suite grows by ≥12 tests, total stays green.
8. Re-running `discover.py --utah-remote` (no other flags) imputes comp
   on ≥30 of the 40 Utah roles currently sitting at `unverified`.

## Pre-conditions

- [ ] `pyyaml` is already in `requirements.txt` (verify with
      `grep -i pyyaml requirements.txt`)
- [ ] `careerops/score.py::score_comp` exists at line ~25 with the
      current 55-default behavior
- [ ] `careerops/pipeline.py::upsert_role` exists and returns the
      role id
- [ ] `careerops/score.py::score_company_tier` exists — reuse its
      one-direction substring matcher convention for `lookup_company`
- [ ] `tests/` currently has 228 passing tests (sanity-check baseline
      before starting: `.venv/bin/pytest tests/ -q | tail -3`)
- [ ] `modes/_shared.md` already loaded — read it to match tone and
      lane vocabulary before authoring `modes/levels-refresh.md`

## Steps

### Step 1 — Author `data/levels_seed.yml`

**Critical:** the executor MUST visit Levels.fyi during execution to
populate accurate values for at least the top 30 companies. Do NOT
fabricate numbers — use `WebFetch` or open browser tabs against
`https://www.levels.fyi/companies/<slug>/salaries` per company.
For any company without a Levels.fyi presence, mark `unknown: true`
and skip the bands; that is the honest answer.

File header (verbatim):

```yaml
# Coin — Levels.fyi comp seed
# Source: Levels.fyi (manual curation). Quarterly refresh required.
# Run `/coin levels-refresh` to walk through stale entries.
#
# Bands are USD. base_p* are annual base salary at the level.
# rsu_4yr_p50 is the median 4-year RSU grant total (NOT annualized).
# bonus_p50 is the target annual bonus.
#
# Levels keys: L4, L5, L6, staff, principal, director, vp.
# Use whichever rungs the company's actual ladder publishes.
```

Top-level shape:

```yaml
companies:
  Filevine:
    last_refreshed: 2026-04-27
    source_url: https://www.levels.fyi/companies/filevine/salaries
    levels:
      L5:
        base_p25: 145000
        base_p50: 165000
        base_p75: 185000
        rsu_4yr_p50: 120000
        bonus_p50: 15000
      staff:
        base_p25: 175000
        base_p50: 195000
        base_p75: 220000
        rsu_4yr_p50: 200000
        bonus_p50: 25000
  Awardco:
    last_refreshed: 2026-04-27
    source_url: https://www.levels.fyi/companies/awardco/salaries
    levels: { ... }
  # ... ~50 entries total
  SomeObscureCo:
    last_refreshed: 2026-04-27
    unknown: true
    source_url: https://www.levels.fyi/  # searched; no presence
```

**Initial seed (~50 companies — populate every one):**

Utah-anchored: Filevine, Awardco, Weave, MasterControl, Pluralsight,
Lucid, Podium, Recursion, Domo, Adobe (Lehi), Qualtrics, Workfront,
Vivint, Spiff.

Remote-friendly target list: Datadog, Hashicorp, MongoDB, Confluent,
Cloudflare, Snowflake, Stripe, Block, Notion, Linear, Vercel,
Hightouch, Census, Retool, Airbyte, Fivetran, dbt Labs, Sourcegraph,
Replit, RevenueCat, Webflow, Plaid, Brex, Ramp, Mercury, Anthropic,
OpenAI, Scale, Crusoe, Anduril, Palantir.

Sanity check the file with `python -c "import yaml; yaml.safe_load(open('data/levels_seed.yml'))"` — must not raise.

### Step 2 — Author `careerops/levels.py`

```python
"""Comp imputation from the curated Levels.fyi seed.

Reads data/levels_seed.yml once, caches the parse, and exposes
lookup + impute helpers for the scoring + pipeline layers.
"""
```

Functions to implement:

- `load_levels_seed() -> dict` — read YAML once, cache in a module-level
  `_SEED_CACHE`. Subsequent calls return the cache. Expose a
  `_reset_cache()` helper for tests.

- `lookup_company(company: str) -> dict | None` — fuzzy match. Steps:
  1. Lowercase input, strip trailing `, Inc.`, ` Inc.`, ` LLC`, ` Ltd`,
     `, Inc`, `.io`, ` Corp`, ` Corporation`.
  2. Exact lowercase key match against `companies` first.
  3. Fall back to one-direction substring (`needle in haystack` only —
     not the reverse) — same convention as `score_company_tier`.
  4. Return the full company dict (including `levels`, `last_refreshed`,
     `source_url`, possibly `unknown`).
  5. Return `None` if no match OR if the matched entry has
     `unknown: true`.

- `impute_comp(company: str, role_title: str | None = None) -> dict | None`:
  1. `entry = lookup_company(company)`. If `None`, return `None`.
  2. Pick the level. If `role_title` contains (case-insensitive)
     `staff`, prefer `staff`; `principal` → `principal`; `director` →
     `director`; `vp` or `vice president` → `vp`. Otherwise use the
     company's "default" level — the highest of `L5`, `staff` that
     exists. Confidence = 0.7 if title-matched; 0.5 if defaulted.
  3. If the chosen level isn't present in the company's ladder, walk
     down: `principal → staff → L6 → L5 → L4`. Lower confidence by
     0.1 per fallback step (floor 0.3). If nothing matches, return
     `None`.
  4. Compute `comp_min = base_p25 + (rsu_4yr_p50 / 4) + bonus_p50`
     and `comp_max = base_p75 + (rsu_4yr_p50 / 4) + bonus_p50`. Round
     to the nearest $1K.
  5. Return:
     ```python
     {
       'comp_min': comp_min,
       'comp_max': comp_max,
       'comp_source': 'imputed_levels',
       'level_matched': '<level key>',
       'confidence': 0.7,  # or 0.5, or stepped-down
     }
     ```

- `get_seed_age(company: str) -> int | None` — days between
  `last_refreshed` and `date.today()`. Return `None` if company not in
  seed.

- `flag_stale(threshold_days: int = 90) -> list[str]` — sorted list of
  company names whose seed is older than threshold. Used by the
  v2.1 levels-refresh mode.

Edge cases to handle: missing `levels` key (treat as `unknown`),
malformed `last_refreshed` (skip — log a warning to stderr), empty
file (`load_levels_seed` returns `{'companies': {}}`).

### Step 3 — Extend `careerops/score.py::score_comp`

Current behavior (per `careerops/score.py:25`):
- Verified comp scored against the lane's comp range.
- `comp_source='unverified'` → hard 55.

New behavior:

```python
def score_comp(role, lane):
    src = role.get('comp_source')
    if src == 'imputed_levels':
        raw = _score_against_lane_range(role, lane)  # existing helper
        confidence = role.get('comp_confidence', 0.5)
        return raw * (0.5 + 0.5 * confidence)
    if src == 'unverified':
        return 55  # unchanged
    return _score_against_lane_range(role, lane)
```

Don't promote imputed comp above verified. A P50 imputation with
confidence 0.7 scores at 85% of its raw value; with confidence 0.5
scores at 75%. Honest discount, transparent in the audit trail.

The `comp_confidence` field needs to flow from `impute_comp` through
the pipeline; see Step 4 — store it in the role row's `notes` field
prefix or add a dedicated column if the schema permits a clean
migration. Prefer a dedicated `comp_confidence REAL` column via
`ALTER TABLE roles ADD COLUMN comp_confidence REAL` in
`pipeline.py::_init_db`. Keep idempotent (`try/except sqlite3.OperationalError`).

### Step 4 — Wire the pipeline auto-impute hook

In `careerops/pipeline.py::upsert_role`, after the row is inserted/
updated, check:

```python
if role.get('comp_source') == 'unverified':
    from careerops.levels import impute_comp
    imputed = impute_comp(role['company'], role.get('title'))
    if imputed:
        cur.execute(
            "UPDATE roles SET comp_min=?, comp_max=?, comp_source=?, "
            "comp_confidence=?, notes=COALESCE(notes,'') || ? "
            "WHERE id=?",
            (
                imputed['comp_min'],
                imputed['comp_max'],
                imputed['comp_source'],
                imputed['confidence'],
                f"\n[imputed comp from Levels.fyi seed: {imputed['level_matched']} @ confidence {imputed['confidence']}]",
                role_id,
            ),
        )
        conn.commit()
```

Auto-imputes during discovery without a separate pass. Idempotent:
the next `upsert_role` for the same role will see
`comp_source='imputed_levels'` and skip the block.

### Step 5 — Author `modes/levels-refresh.md` (skeletal stub)

Match the format of `modes/audit.md` and `modes/track.md`. Sections:

1. **When this fires** — `/coin levels-refresh` and only that.
2. **Workflow** — narrative:
   1. Call `flag_stale(90)` and surface the list. If empty, exit
      with "Seed is fresh. Next refresh due <oldest + 90 days>."
   2. For each stale company, in order:
      - Print the seed entry.
      - Open `https://www.levels.fyi/companies/<slug>/salaries` in
        the user's browser (or print the URL).
      - Ask Sean for the current P25/P50/P75 base + RSU + bonus per
        level (one prompt per level the company has).
      - Atomically update `data/levels_seed.yml` with the new bands
        and `last_refreshed: <today>`.
   3. After all companies processed, print a summary: how many
      refreshed, how many skipped, and the new "next refresh due" date.
3. **Non-goals** — does NOT scrape Levels.fyi automatically. Does NOT
   modify scoring weights. Does NOT touch role rows.
4. **v2.1 note** — the initial implementation is manual: agent reads
   the YAML, opens the URLs, walks Sean through the inputs, edits the
   file inline. A future iteration may add `scripts/levels_refresh.py`
   for batch operation.

### Step 6 — SKILL.md routing

Find the SKILL.md routing table (`.claude/skills/coin/SKILL.md`). Add
a row:

| Trigger | Mode | Notes |
|---|---|---|
| `levels-refresh` | `modes/levels-refresh.md` | Quarterly comp seed refresh |

If there's a `Sub-commands` enumeration in `.claude/commands/coin.md`
include `levels-refresh` there too.

### Step 7 — Tests at `tests/test_levels_crossref.py`

Exactly these 12+ tests (add more as defensive coverage warrants):

1. `test_yaml_loads_and_validates_structure` — file parses,
   `companies` is a dict, every entry has `last_refreshed` and either
   `levels` or `unknown: true`.
2. `test_lookup_company_exact_match` — `lookup_company('Filevine')`
   returns the entry.
3. `test_lookup_company_fuzzy_match_inc_stripped` —
   `lookup_company('Datadog, Inc.')` returns the Datadog entry.
4. `test_lookup_company_fuzzy_match_lowercase` — `lookup_company('stripe')`
   returns the Stripe entry.
5. `test_lookup_company_one_direction_substring` —
   `lookup_company('Hashicorp Vault')` matches Hashicorp; reverse
   (`lookup_company('Hash')`) does NOT match.
6. `test_lookup_company_miss_returns_none` —
   `lookup_company('Acme Quantum Pickleball')` returns `None`.
7. `test_lookup_company_unknown_returns_none` — a company seeded with
   `unknown: true` returns `None`.
8. `test_impute_comp_title_matches_staff_level` —
   `impute_comp('Filevine', 'Staff Solutions Engineer')` returns
   `level_matched='staff'`, `confidence=0.7`.
9. `test_impute_comp_default_level_for_senior_title` —
   `impute_comp('Filevine', 'Senior Sales Engineer')` falls back to
   the company's default level, `confidence=0.5`.
10. `test_impute_comp_unknown_company_returns_none`.
11. `test_score_comp_imputed_applies_confidence_haircut` — a role
    with `comp_source='imputed_levels'` and `comp_confidence=0.7` scores
    at 85% of the raw band score.
12. `test_score_comp_unverified_returns_55` — regression guard.
13. `test_upsert_role_auto_imputes_when_unverified` — insert a role
    for Filevine with `comp_source='unverified'`, then re-fetch from
    DB; assert `comp_source='imputed_levels'`, `comp_min` and
    `comp_max` populated, `notes` contains "imputed comp from
    Levels.fyi seed".
14. `test_get_seed_age_returns_none_for_unknown_company`.
15. `test_get_seed_age_returns_days_for_known_company`.
16. `test_flag_stale_filters_by_threshold` — write a temp seed with
    one fresh and one 100-days-old entry; `flag_stale(90)` returns only
    the old one.

Use `tmp_path` + monkeypatched `_SEED_CACHE` to isolate seed-file
tests from the real `data/levels_seed.yml`.

### Step 8 — Audit-mode interaction

Open `modes/audit.md` and find Check 5 (metric provenance). Add a
sub-bullet:

> Imputed comp (`comp_source='imputed_levels'`) MUST NEVER appear in
> resume executive summary, top bullets, or any prose. It is for
> internal scoring only. If the tailored resume references a salary
> band derived from imputed comp, flag CRITICAL.

This protects against the same fabrication failure mode the
2026-04-24 code review caught with Cox/TitanX inflation.

### Step 9 — Run discover and verify the impute hit rate

```bash
.venv/bin/python scripts/discover.py --utah-remote
.venv/bin/python -c "
from careerops.pipeline import _conn
c = _conn()
n_imp = c.execute(\"SELECT COUNT(*) FROM roles WHERE comp_source='imputed_levels'\").fetchone()[0]
n_unv = c.execute(\"SELECT COUNT(*) FROM roles WHERE comp_source='unverified'\").fetchone()[0]
print(f'imputed: {n_imp} | still unverified: {n_unv}')
"
```

Expect ≥30 imputed (Filevine, Awardco, Weave, etc. all in seed).

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short
# Expect: 240+ passed (228 baseline + 12 new), 0 failed

.venv/bin/python -c "import yaml; yaml.safe_load(open('data/levels_seed.yml')); print('YAML OK')"

.venv/bin/python -c "
from careerops.levels import impute_comp
r = impute_comp('Filevine', 'Sales Engineer')
print(r)
assert r is not None, 'Filevine should impute'
assert 130_000 <= r['comp_min'] <= 190_000, f\"comp_min out of range: {r['comp_min']}\"
print('Filevine impute sanity check passed')
"

# Audit-mode regression — make sure no resume references imputed comp
grep -rn 'imputed_levels' data/resumes/generated/ && echo "FAIL: imputed comp leaked into resume" || echo "OK: no imputed comp in resumes"
```

- [ ] `data/levels_seed.yml` exists, valid YAML, ~50 companies
- [ ] `careerops/levels.py` exists with all 5 helpers
- [ ] `score_comp` honors `imputed_levels` with confidence haircut
- [ ] `upsert_role` auto-imputes for known companies
- [ ] `modes/levels-refresh.md` exists
- [ ] SKILL.md routes `/coin levels-refresh` correctly
- [ ] `tests/test_levels_crossref.py` has 12+ tests, all passing
- [ ] `modes/audit.md` Check 5 includes the imputed-comp guard
- [ ] Re-running discover bumps ≥30 of 40 Utah roles to `imputed_levels`
- [ ] `pytest tests/` total: 240+ passed, 0 regressions

## Definition of Done

- [ ] All Verification checkboxes ticked
- [ ] `docs/state/project-state.md` updated with the new mode and the
      seed file location
- [ ] `git status` shows: new `data/levels_seed.yml`,
      `careerops/levels.py`, `modes/levels-refresh.md`,
      `tests/test_levels_crossref.py`; modified `careerops/score.py`,
      `careerops/pipeline.py`, `modes/audit.md`,
      `.claude/skills/coin/SKILL.md`, `.claude/commands/coin.md`
- [ ] Commit message follows the `Authored by: Sean @ coin` convention

## Rollback

```bash
rm data/levels_seed.yml careerops/levels.py modes/levels-refresh.md tests/test_levels_crossref.py
git checkout careerops/score.py careerops/pipeline.py modes/audit.md .claude/skills/coin/SKILL.md .claude/commands/coin.md docs/state/project-state.md
# Revert the column add (only needed if a fresh DB was created):
.venv/bin/python -c "
import sqlite3
c = sqlite3.connect('data/db/pipeline.db')
# SQLite cannot DROP COLUMN pre-3.35 — leave the column, it'll be ignored.
print('comp_confidence column left in place; harmless.')
"
```

Existing scoring + pipeline behavior remains intact since the new
code paths are additive (`comp_source='imputed_levels'` is a new
sentinel; `unverified` still scores 55).

## Style notes for the executor

- The seed file is the source of truth — visit Levels.fyi during
  execution. Do NOT fabricate bands. Mark `unknown: true` if no
  Levels.fyi data exists.
- The `notes` field on the role row must say "imputed" so the audit
  trail is transparent. Audit mode Check 5 enforces that imputed
  comp never leaks into resume copy.
- Future-compat: `last_refreshed` per company is the hook the v2.1
  `/coin levels-refresh` mode reads. Get the field name and date
  format right now so the future task is plumbing only.
- Reuse `score_company_tier`'s one-direction substring matcher
  convention for `lookup_company` — don't invent a new fuzzy-match
  algorithm.
- The score haircut formula `raw * (0.5 + 0.5 * confidence)` is
  deliberate: at confidence 1.0 it's full credit, at 0.0 it's half.
  Don't tune the constants; they're the agreed honesty discount.
