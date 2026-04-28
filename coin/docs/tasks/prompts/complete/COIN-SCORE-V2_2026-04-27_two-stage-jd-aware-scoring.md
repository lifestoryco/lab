---
task: COIN-SCORE-V2
title: Two-stage JD-aware scoring — stage 1 fast title score, stage 2 deep JD score for top-N
phase: Scoring v2
size: XL
depends_on: COIN-SCRAPER-POSTED-AT, COIN-DISQUALIFIERS, COIN-MULTI-BOARD, COIN-LEVELS-CROSSREF
created: 2026-04-27
---

# COIN-SCORE-V2: Two-stage JD-aware scoring

## Context

Today's discover at title-only scoring produced 4 misclassified roles in the most recent dashboard run:

- **#4** — ITAR / composite materials role scored **72.4** (B-) on title keywords alone; the JD reveals manufacturing-floor + clearance gates that disqualify Sean entirely
- **#9** — Secret clearance position scored **72.4**; clearance is a hard DQ for Sean
- **#13** — Microsoft-stack PM role scored **72.4**; JD demands Azure/Power Platform Sean has zero exposure to
- **#14** — Cybersecurity advisor role scored **72.4**; not a TPM/SE/SA/RevOps lane fit at all

All four scored identically because the score is **JD-blind**. `discover.py:46` calls `score.score_fit(role, lane)` with no `parsed_jd` argument, so the rubric collapses to title-keyword + company-tier signal. JDs are only fetched if Sean runs `/coin score N` manually after the fact. Result: the dashboard's top picks aren't actually the best matches — they're just the best title-keyword matches. Sean wastes triage time every dashboard refresh.

The fix is structural: **make discovery 2-stage**.

- **Stage 1 (current, fast):** scrape → cheap title/company score → store. Same as today.
- **Stage 2 (new, smart):** for top-N (default 15), fetch JD, parse JD via the host Claude session, re-score with `parsed_jd` populated. Persist as a separate column so we can A/B compare.
- **Dashboard:** show stage 2 if present, else stage 1, with a small `S1` / `S2` badge so Sean knows which signal he's reading.

This pre-supposes four other tasks have shipped (see Pre-conditions). Without them, stage 2 has nothing meaningful to score against — the rubric still collapses.

**Critical architecture note:** the LLM call that parses the JD is made by **the host Claude Code session executing `modes/discover.md`**, NOT by a Python `anthropic` SDK call. Per `CLAUDE.md` rule #6 ("No Anthropic API calls"), Coin runs entirely inside Sean's Claude Code subscription. The Python script writes a pending-work file; the agent reads it and does the parsing as part of executing the mode. This is the same pattern `modes/score.md` already uses for single-role JD parsing.

## Goal

After this task ships, `python scripts/discover.py --location "Utah, United States" --deep-score 15` produces a dashboard where:

1. The 40+ roles each have a `score_stage1` (title + company tier, JD-blind, fast)
2. The top 15 by `score_stage1` also have `score_stage2` (JD-aware, disqualifier-aware, comp-aware)
3. The top picks displayed on `dashboard.py` reflect `COALESCE(score_stage2, score_stage1)`, with a badge indicating which stage is authoritative
4. Hard-disqualified roles (clearance required, ITAR, etc.) are auto-quarantined to `out_of_band` lane during stage 2
5. The #4 / #13 / #14 class of misclassification gets corrected — those roles either drop in score, get DQ'd, or surface their actual fit signal honestly

## Pre-conditions

These MUST land before COIN-SCORE-V2. Stage 2 has no teeth without them.

- [ ] `COIN-SCRAPER-POSTED-AT` — adds `posted_at` column and `score_freshness` rubric dimension. Stage 2 needs freshness signal to penalize 60-day-old reposts.
- [ ] `COIN-DISQUALIFIERS` — adds `careerops/disqualifiers.py` with `scan_jd(jd_text, profile) -> dq_result` and the `dq_result` parameter to `score_breakdown`. Stage 2 calls this every time.
- [ ] `COIN-MULTI-BOARD` — multiplies role count beyond LinkedIn-only. More roles = more JDs to fetch in stage 2. Validate stage 2 stays under ~5 minutes for top-15 even when stage 1 produces 100+ roles.
- [ ] `COIN-LEVELS-CROSSREF` — auto-imputes comp during stage 1 so stage 2 sees real comp numbers in `parsed_jd['comp_min/max']` even when the posting omits them.

If any pre-condition is not yet merged, STOP and surface the dependency. Do not partially implement — the rubric depends on the full chain.

## Scope

### 1. New migration `coin/scripts/migrations/m006_two_stage_score.py`

Follow the m003 / m004 idempotent pattern. PRAGMA-check before each ALTER.

Adds columns to `roles` table:

| Column | Type | Default | Purpose |
|---|---|---|---|
| `score_stage1` | REAL | NULL | Original fit_score behavior — title + company tier, JD-blind |
| `score_stage2` | REAL | NULL | Deep score after JD fetch + parse (NULL until stage 2 runs) |
| `score_stage` | INTEGER | 1 | Which stage is currently authoritative (1 or 2) |
| `jd_parsed_at` | TEXT | NULL | ISO timestamp of last stage-2 score |

**Backfill:** copies existing `fit_score` → `score_stage1` for all rows where `fit_score IS NOT NULL`. Existing `fit_score` column **stays in place** as a derived value. Going forward, `pipeline.get_role` returns `fit_score = COALESCE(score_stage2, score_stage1)` — but the raw column still exists for backwards compat with any code that reads it directly.

Writes a row to `schema_migrations` table per the m003 pattern.

Idempotency: re-running the migration is a no-op (PRAGMA confirms columns exist, skip ALTERs, skip backfill if `score_stage1` already populated).

### 2. `coin/careerops/pipeline.py` updates

**`init_db` schema:**
Add the four new columns to the `CREATE TABLE roles` statement so fresh databases get them at create time.

**New helpers:**

```python
def update_score_stage1(role_id: int, score: float) -> None:
    """Persist stage-1 score. Sets score_stage=1 if score_stage2 is NULL."""

def update_score_stage2(
    role_id: int,
    score: float,
    parsed_jd: dict,
    jd_parsed_at: str,
) -> None:
    """Persist stage-2 score + parsed_jd JSON + timestamp. Sets score_stage=2."""

def get_top_n_for_deep_score(
    n: int = 15,
    lane: str | None = None,
    since_days: int = 7,
) -> list[dict]:
    """Top-N roles by score_stage1 that don't yet have score_stage2 populated.
    Filters: status in ('discovered', 'scored'), score_stage2 IS NULL,
    discovered_at >= now - since_days. Optional lane filter."""
```

**`update_jd_parsed(role_id, parsed_dict)`** — already exists. Update it to also set `jd_parsed_at = datetime.utcnow().isoformat()`.

**`get_role(role_id)`** — update return shape so the dict contains:
- `fit_score`: `COALESCE(score_stage2, score_stage1)` (computed at read time)
- `_stage`: `'S2'` if `score_stage2 IS NOT NULL` else `'S1'`
- The raw `score_stage1`, `score_stage2`, `score_stage`, `jd_parsed_at` columns also returned for callers that want them

### 3. `coin/careerops/score.py` updates

**No formula changes.** Those already shipped in COIN-SCRAPER-POSTED-AT and COIN-DISQUALIFIERS. This task only adds explicit stage helpers so callers don't have to remember the kwarg dance.

```python
def score_stage1(role: dict, lane: str) -> dict:
    """JD-blind title + company-tier score. Used in discovery first pass.
    Internally: score_breakdown(role, lane, parsed_jd=None, dq_result=None).
    Returns the same breakdown shape as score_breakdown."""

def score_stage2(role: dict, lane: str, parsed_jd: dict, dq_result: dict) -> dict:
    """Full JD-aware + disqualifier-aware score. Used in deep-score pass.
    Internally: score_breakdown(role, lane, parsed_jd=parsed_jd, dq_result=dq_result).
    Returns the same breakdown shape as score_breakdown."""
```

Both helpers return the same dict shape (`{composite, dimensions, grade}`) so downstream consumers don't branch on stage.

### 4. `coin/scripts/discover.py` updates

Stage 1 unchanged — preserves the existing flow. After stage 1 completes:

**New CLI flag:** `--deep-score N` (default 15, 0 = disable)

When `N > 0`:
1. Take top-N by `score_stage1` from the just-completed pass (filter: lane in 4 archetypes, status `discovered`, optional `--lane <name>` if user passed one)
2. For each role:
   - Call `scraper.fetch_jd(url)` (already exists at `scraper.py:241`)
   - Call `pipeline.update_jd_raw(role_id, jd_text)`
3. Write a state file `data/.deep_score_pending.json` listing the role IDs queued for parsing:

```json
{
  "created_at": "2026-04-27T15:32:00Z",
  "discover_run_id": "<uuid or timestamp>",
  "role_ids": [11, 19, 22, 31, 38, ...]
}
```

4. Print a marker line to stdout that `modes/discover.md` looks for:

```
### DEEP-SCORE-PENDING count=15 file=data/.deep_score_pending.json
```

**The script does NOT call any LLM.** It only fetches the raw JD HTML, persists it to `jd_raw`, and signals the host session that 15 JDs are ready for parsing. Per CLAUDE.md rule #6, all reasoning runs in the host Claude Code session — `discover.py` is pure I/O.

If `--deep-score 0`, skip the entire stage-2 prep block and do NOT write the pending file.

### 5. `coin/modes/discover.md` rewrite

The current Step 4 is "Apply rubric narration" (a single-pass narrate-the-results step). Replace it with a Stage 2 loop, then a Bloomberg-cards step, then Sean's pick.

#### Step 4a — Deep-score (auto when `--deep-score N` was passed, default 15)

After `discover.py` exits, check for the marker line in stdout (`### DEEP-SCORE-PENDING`). If present:

1. Read `data/.deep_score_pending.json` for role IDs to deep-score
2. For each `role_id` in the list:
   1. Read the role's `jd_raw` from the DB (already fetched and persisted by `discover.py`)
   2. Parse the JD into a structured dict using **THIS reasoning prompt** (verbatim — the agent reading this mode file uses it):

```
Extract from this JD into a JSON object with exactly these keys:

- required_skills: list[str]      # must-have skills explicitly listed in "Requirements" or "Must have"
- preferred_skills: list[str]     # nice-to-have skills from "Preferred" or "Bonus"
- seniority: str                  # one of: 'junior'|'mid'|'senior'|'staff'|'principal'|'director'|'vp'|''
- comp_min: int|null              # parse $XXXk-$YYYk patterns, USD; null if not stated
- comp_max: int|null              # null if not stated
- comp_currency: str              # 'USD' default, 'CAD'|'EUR'|'GBP' if explicit
- comp_explicit: bool             # true if comp band is in the JD; false if absent
- red_flags: list[str]            # e.g. "10x engineer language", "unlimited PTO with no minimum",
                                  #      "wear many hats", "fast-paced startup environment",
                                  #      "ninja/rockstar/guru language"
- culture_signals: list[str]      # e.g. "remote-first", "async", "no on-call", "4-day week",
                                  #      "core hours overlap", "documented onboarding"
- team_size: int|null             # if mentioned ("team of 8")
- reporting_to: str|null          # e.g. "VP of Engineering", "CTO", "Head of Product"
- location_flexibility: str       # one of: 'remote'|'hybrid'|'onsite'|'remote-us'|'remote-global'|''

Output ONLY the JSON object. No prose, no code fence, no commentary.
```

   3. Run `careerops.disqualifiers.scan_jd(jd_raw, PROFILE)` → `dq_result`
   4. **If `dq_result['hard_dq']` is True:**
      - Call `pipeline.update_lane(role_id, 'out_of_band')`
      - Call `pipeline.update_status(role_id, 'no_apply')` with note `"hard_dq: " + dq_result['reasons'][0]`
      - **SKIP the stage-2 score call** — the role is now quarantined and shouldn't sit in the dashboard top-N. Move to next role.
   5. **Else:**
      - Call `pipeline.get_role(role_id)` to get the latest row
      - Call `score.score_stage2(role, lane, parsed_jd, dq_result)` → `breakdown`
      - Call `pipeline.update_score_stage2(role_id, breakdown['composite'], parsed_jd, datetime.utcnow().isoformat())`
3. Delete `data/.deep_score_pending.json` after the entire loop completes
4. Print a one-line summary: `Deep-scored N roles. M hard-DQ'd, K re-scored.`

**Note:** Stage 2 does **NOT** auto-tailor. It only re-scores. Tailoring still requires explicit `/coin tailor N`. This separation is intentional: re-scoring 15 roles is cheap reasoning work; tailoring 15 resumes would be expensive both in tokens and in Sean's review time.

#### Step 4b — Bloomberg-style cards (existing)

Render the Rich-style cards as before, but each card now shows the stage badge inline next to the score:

```
[#4]  Filevine — Sales Engineer
      Lane: enterprise-sales-engineer  ·  Fit: 78.4 (B+) [S2]  ·  SLC, UT
      ...
```

Cards with `_stage == 'S1'` show `[S1]` so Sean knows the score isn't yet JD-aware.

#### Step 5 — Sean's pick (unchanged)

Same as before — agent recommends one role from the top-3, citing the parsed JD's specific signals (now available because stage 2 has run).

### 6. `coin/scripts/dashboard.py` updates

Show a small badge next to each role's fit score: `S1` (gray) or `S2` (cyan). Use Rich's `Text` markup. The badge appears in the existing fit-score column — no new column, just a 4-character suffix (` [S1]` or ` [S2]`).

If a future web UI ships, the badge will be click-through and reveal the parsed_jd contents in a popover. For now, terminal-only.

### 7. Tests in `coin/tests/`

#### `test_two_stage_discover.py` (8 tests, new file)

1. Stage 1 score is persisted to `score_stage1` (via `update_score_stage1`)
2. Stage 2 score is persisted to `score_stage2` AND `jd_parsed_at` is set (via `update_score_stage2`)
3. `get_top_n_for_deep_score(n=10)` returns roles with `score_stage1 IS NOT NULL` and `score_stage2 IS NULL`, ordered by `score_stage1 DESC`
4. `--deep-score 0` disables stage 2 entirely (no pending file written, no JDs fetched)
5. `--deep-score 5` writes exactly 5 role IDs to the pending file (assert file contents)
6. `update_jd_parsed(role_id, parsed_dict)` sets `jd_parsed_at` to a recent ISO timestamp (within last 5 seconds)
7. `get_role(role_id)` returns `fit_score = COALESCE(score_stage2, score_stage1)` and `_stage = 'S2'` when stage 2 is populated, `_stage = 'S1'` otherwise
8. Re-running deep-score on a role that already has `score_stage2` cleanly overwrites the prior value (no INSERT-or-IGNORE skip, no duplicate row)

#### `test_migrations_m006.py` (4 tests, new file)

1. Schema columns applied: `score_stage1`, `score_stage2`, `score_stage`, `jd_parsed_at` exist after migration
2. Idempotency: running m006 twice produces identical schema, no errors
3. Backfill: pre-existing `fit_score` values are copied to `score_stage1`
4. `schema_migrations` row is inserted with `version='m006'` and a timestamp

#### `test_score_stage_helpers.py` (3 tests, new file)

1. `score_stage1(role, lane)` returns a breakdown dict with no JD signal contributing (assert dimensions['skills_match'] uses title-only fallback)
2. `score_stage2(role, lane, parsed_jd, dq_result)` returns a breakdown dict that incorporates parsed_jd (assert dimensions['skills_match'] differs from stage1 when parsed_jd has explicit required_skills)
3. Both helpers return the same dict shape: `{composite: float, dimensions: dict, grade: str}` — same keys at top level

#### `test_discover_mode_stage2_doc.py` (2 tests, new file)

These guard the modes file so future edits don't silently break the agent contract.

1. `modes/discover.md` contains the literal string `Step 4a — Deep-score`
2. `modes/discover.md` contains the literal substring `required_skills: list[str]` AND `Output ONLY the JSON object` (proves the JD-parsing prompt block is intact)

## Acceptance

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short
```

- [ ] Test count: previously 228 baseline + Sprint 1 deltas + 17 new (8 + 4 + 3 + 2) = **290+ tests passing**
- [ ] No regressions in existing scoring tests (`test_score.py`, `test_score_breakdown.py`)

```bash
.venv/bin/python scripts/discover.py --location "Utah, United States" --deep-score 15
```

- [ ] Returns standard JSON output as before (no breaking change to script contract)
- [ ] Writes `data/.deep_score_pending.json` with exactly 15 role IDs (or fewer if fewer than 15 new roles surfaced)
- [ ] Prints `### DEEP-SCORE-PENDING count=15 file=data/.deep_score_pending.json` to stdout
- [ ] Subsequent host-session-driven parse loop (executing `modes/discover.md` Step 4a) populates `score_stage2` on those 15 roles
- [ ] Top picks now reflect JD-aware scores — the #4 / #13 / #14 class of misclassification is corrected (either DQ'd to `out_of_band` or re-scored to a more honest number)

```bash
.venv/bin/python -c "from careerops.pipeline import get_role; r = get_role(11); print(r['fit_score'], r.get('_stage'))"
```

- [ ] Prints the stage-2 score (e.g. `78.4`) and `S2`
- [ ] If role 11 has only stage 1, prints the stage-1 score and `S1`

```bash
.venv/bin/python scripts/dashboard.py
```

- [ ] Each role row shows `[S1]` or `[S2]` badge next to its fit score

## Style notes for the executor

- **Be EXPLICIT** in `modes/discover.md` Step 4a that the LLM call is from **the host Claude Code session** (the agent reading the mode file), NOT a Python `OpenAI`/`Anthropic` API call. Reference CLAUDE.md rule #6.
- **The prompt block for JD parsing must be written verbatim** in `modes/discover.md` so the executing agent has the exact schema. Do not summarize it. Copy the full block from Section 5 above into the mode file inside a fenced code block.
- **Reference the user's specific complaint** about #4 / #13 / #14 false positives in the mode file's intro paragraph for Step 4a — this anchors the "why" so future maintainers don't refactor it away.
- **Stage 1 stays fast**: no JD fetch, no LLM call. First dashboard view is still ~2 min for 40 roles. Stage 2 adds ~3-5 min for top-15 (one `fetch_jd` HTTP call + one parse-prompt per role). Document this latency budget in the mode file so Sean knows what to expect.
- **Idempotency is mandatory** for the migration — m006 must be safe to re-run. Follow the m003 / m004 PRAGMA pattern exactly.
- **No anthropic dependency added.** Verify with `pip list | grep -i anthropic` after changes — must still report absent.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin

# Full test suite
.venv/bin/pytest tests/ -q --tb=short

# Migration round-trip
.venv/bin/python scripts/migrations/m006_two_stage_score.py
.venv/bin/python scripts/migrations/m006_two_stage_score.py  # second run = no-op

# Schema verification
.venv/bin/python -c "
import sqlite3
con = sqlite3.connect('data/db/pipeline.db')
cols = [r[1] for r in con.execute('PRAGMA table_info(roles)')]
for c in ['score_stage1', 'score_stage2', 'score_stage', 'jd_parsed_at']:
    assert c in cols, f'missing {c}'
print('schema OK')
"

# Stage 1 only
.venv/bin/python scripts/discover.py --location "Utah, United States" --deep-score 0
# Expect: no data/.deep_score_pending.json written

# Full pass with deep-score
.venv/bin/python scripts/discover.py --location "Utah, United States" --deep-score 15
# Expect: marker line, pending file with 15 IDs

# Then run /coin discover from inside Claude Code to drive Step 4a end-to-end

# Confirm no anthropic dep
.venv/bin/pip list | grep -i anthropic || echo "anthropic: absent ✓"
```

## Definition of Done

- [ ] Migration `m006_two_stage_score.py` exists, idempotent, backfills `fit_score → score_stage1`
- [ ] `pipeline.py` has `update_score_stage1`, `update_score_stage2`, `get_top_n_for_deep_score`; `update_jd_parsed` sets `jd_parsed_at`; `get_role` returns COALESCE'd `fit_score` + `_stage`
- [ ] `score.py` has `score_stage1` and `score_stage2` helper wrappers around `score_breakdown`
- [ ] `discover.py` accepts `--deep-score N`, fetches JDs for top-N, writes pending file, prints marker line
- [ ] `modes/discover.md` Step 4a documents the loop verbatim, including the JD-parsing prompt block
- [ ] `dashboard.py` shows `[S1]` / `[S2]` badges
- [ ] All 17 new tests pass; total suite at 290+ passing
- [ ] Manual run of `/coin discover` corrects at least one of {#4, #13, #14} class of misclassification
- [ ] `docs/state/project-state.md` updated with the new scoring stage description
- [ ] No `anthropic` package added to requirements

## Rollback

```bash
# 1. Drop the new columns (sqlite has no DROP COLUMN pre-3.35; use a rebuild if needed)
sqlite3 data/db/pipeline.db <<'SQL'
DELETE FROM schema_migrations WHERE version='m006';
SQL

# 2. Revert source files
git checkout careerops/pipeline.py careerops/score.py scripts/discover.py modes/discover.md scripts/dashboard.py
rm -f scripts/migrations/m006_two_stage_score.py
rm -f tests/test_two_stage_discover.py tests/test_migrations_m006.py tests/test_score_stage_helpers.py tests/test_discover_mode_stage2_doc.py
rm -f data/.deep_score_pending.json

# 3. Restore docs
git checkout docs/state/project-state.md
```

Stage-1-only scoring (the pre-COIN-SCORE-V2 behavior) is preserved by the rollback because `fit_score` was never removed and `score_stage1` columns are dropped. Existing `/coin score N` flow continues to work standalone for one-off JD parses.
