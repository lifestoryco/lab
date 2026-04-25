---
task: COIN-OFERTAS
title: Author modes/ofertas.md — multi-offer comparison + negotiation brief (santifer port)
phase: Modes Build-Out
size: M
depends_on: COIN-AUDIT
created: 2026-04-25
---

# COIN-OFERTAS: Author `modes/ofertas.md`

## Context

Sean is mid-pipeline (Netflix tailored, more applications going out this week). When two or three offers land in the same window — which is the goal — the math gets non-trivial fast: base × signing × annual RSU vesting curve × performance bonus × benefits delta × commute / WFH × growth trajectory × pedigree value × cash-vs-equity risk × tax (state income).

`santifer/career-ops` ships an `ofertas` mode for exactly this: ingest 2+ offers as structured records, compute first-year and three-year TC under each offer's specific vesting schedule, surface the deltas plain-English, and draft a negotiation brief per offer that opens with the strongest counter-anchor.

This is **decision support**, not advocacy — Coin presents the math and the trade-offs; Sean picks. The mode must be ruthlessly factual: never recommend a specific offer; surface the strongest argument for each.

## Goal

Create `modes/ofertas.md` so that `/coin ofertas` (with no args) walks Sean through entering 2+ active offers via AskUserQuestion, persists them to a new `offers` table, computes Y1 and 3-year TC under each offer's vesting schedule (RSUs at grant-date stock price + projected growth), produces a side-by-side comparison table, and drafts a per-offer negotiation counter-brief.

## Pre-conditions

- [ ] At least one role in pipeline has status `offer` (else mode prompts to seed manually)
- [ ] PROFILE.target_state for tax (default UT — 4.65% flat)
- [ ] Coin has access to the `_shared.md` 4-archetypes table for "growth trajectory" scoring

## Steps

### Step 1 — Schema migration

Add `scripts/migrations/002_offers_table.py`:

```sql
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id),
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    received_at DATE NOT NULL,
    expires_at DATE,                          -- offer-deadline pressure
    base_salary INTEGER NOT NULL,             -- annualized USD
    signing_bonus INTEGER DEFAULT 0,
    annual_bonus_target_pct REAL DEFAULT 0,   -- 0.10 = 10%
    annual_bonus_paid_history TEXT,           -- JSON: ["100%", "85%", "120%"] historic payout
    rsu_total_value INTEGER DEFAULT 0,        -- 4-yr grant value at grant-date FMV
    rsu_vesting_schedule TEXT,                -- '25/25/25/25' or '5/15/40/40' (cliff variant)
    rsu_vest_years INTEGER DEFAULT 4,
    rsu_cliff_months INTEGER DEFAULT 12,
    equity_refresh_expected INTEGER DEFAULT 0, -- annual top-up grant (estimate)
    benefits_delta INTEGER DEFAULT 0,         -- vs current — 401k match, healthcare premium, etc.
    pto_days INTEGER,
    remote_pct INTEGER,                       -- 0 / 50 / 100
    state_tax TEXT,                           -- e.g. 'CA' for tax math
    growth_signal TEXT,                       -- free-text: Series B, public, IPO 12mo, etc.
    notes TEXT,
    status TEXT DEFAULT 'active',             -- 'active' | 'declined' | 'accepted' | 'expired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Track in `schema_migrations`. Idempotent (`CREATE TABLE IF NOT EXISTS`).

### Step 2 — Compensation math module

Add `careerops/offer_math.py` (pure functions, no I/O):

- `year_one_tc(offer: dict) -> dict` returns:
  ```python
  {
    'base': offer['base_salary'],
    'signing': offer['signing_bonus'],
    'rsu_y1': offer['rsu_total_value'] * vest_share_y1(offer),  # 0.05 / 0.25 / etc.
    'bonus_y1': offer['base_salary'] * offer['annual_bonus_target_pct'] * historical_hit_rate(offer),
    'total': sum_of_above,
    'effective_after_state_tax': total * (1 - state_tax_rate(offer['state_tax'])),
  }
  ```
- `three_year_tc(offer: dict, rsu_growth_pct: float = 0.0) -> dict` — same shape but summed across Y1+Y2+Y3 with vesting curve applied; `rsu_growth_pct` is a sensitivity knob (default 0 = neutral; +10 = bullish; −20 = bearish)
- `vest_share_y1(offer: dict) -> float` — parses `rsu_vesting_schedule` ('25/25/25/25' = 0.25, '5/15/40/40' = 0.05, '6.25/q' = 0.25 with quarterly granularity); honors `rsu_cliff_months` (cliff > 12 = 0 in Y1)
- `historical_hit_rate(offer: dict) -> float` — averages `annual_bonus_paid_history` if present; default 1.0 (target = paid)
- `state_tax_rate(state_code: str) -> float` — small lookup table (CA=0.093, NY=0.0685, UT=0.0465, WA=0.0, TX=0.0, FL=0.0, ...). Document as approximation, NOT tax advice.
- `delta_table(offers: list[dict]) -> list[dict]` — pairwise deltas with one offer marked `baseline`

All functions must accept dicts (not classes) so they can be called from the mode's bash one-liners.

### Step 3 — Author `modes/ofertas.md`

The mode must instruct the agent to:

**3.1 — Discover existing offers.** Query `roles WHERE status='offer'`. If 0 found, ask Sean: *"No offers in pipeline. Want to enter them manually? (y/n)"*. If yes, use AskUserQuestion to capture company + role for each.

**3.2 — Capture offer details.** For each active offer, walk Sean through structured capture using AskUserQuestion blocks:
- Base salary (free-text → integer)
- Signing bonus (free-text)
- Annual bonus target % (free-text)
- Historical bonus payout (free-text — "team paid 100% last 2 years")
- RSU total grant value (4-yr USD)
- Vesting schedule — AskUserQuestion: 25/25/25/25 even · 5/15/40/40 back-loaded · 6.25/q quarterly even · custom
- Cliff — AskUserQuestion: none · 6mo · 12mo · custom
- Remote % — 0 / 50 / 100
- State (for tax) — defaults to UT for remote roles
- Growth signal — free-text (Series B, public, etc.)
- Offer expiration date — free-text (deadline pressure)

Persist to `offers` table via `careerops.pipeline.insert_offer()` (add this helper).

**3.3 — Compute the comparison.** Run `offer_math.year_one_tc` and `offer_math.three_year_tc` for each. Build a comparison table and surface:

```
═══════════════════════════════════════════════
  Offer Comparison
═══════════════════════════════════════════════

                    Cox-style    Filevine     Verkada
                    --------     --------     --------
Base                $185K        $172K        $195K
Signing             $25K         $0           $40K
RSU Y1 (vest)       $30K         $40K         $25K  (cliff)
Bonus Y1 (hist)     $18K         $17K         $24K
─────────────────────────────────────────────────────
Y1 TOTAL            $258K        $229K        $284K
Y1 after UT tax     $246K        $218K        $271K

3-YR TOTAL          $720K        $680K        $810K
3-YR @ -20% RSU     $695K        $640K        $760K  (downside)
3-YR @ +10% RSU     $740K        $700K        $850K  (upside)

REMOTE              100%         hybrid SLC   100%
EXPIRES             Apr 30       (none)       May 5
```

**3.4 — Per-offer narrative.** For each offer, surface in plain English:
- The strongest argument FOR it (highest dimension delta)
- The biggest risk (cliff + early-stage = "all upside is paper")
- The deadline pressure (if `expires_at` within 7 days, flag in red)

**3.5 — Negotiation counter-brief.** For each non-baseline offer, draft a counter:

```
Counter for Filevine ($229K Y1 vs Verkada $284K):

Anchor: Verkada's $284K Y1 with 100% remote.
Ask: Bump base from $172K → $185K and add $25K signing.
Justification (pick what's true):
  - 15+ yr in B2B SaaS / IoT pre-sales (Utah Broadband ARR scale-up)
  - PMP + MBA
  - Local hire (no relocation cost)
Concession lever: accept hybrid SLC if base hits $185K.
Best alternative: walk to Verkada — cleaner remote, larger Y1 TC.
```

Counters MUST cite *real* PROFILE proof points (drawn from `data/resumes/base.py`) — never invent. If Sean lacks a leverage point, say "no anchor available on this dimension".

**3.6 — Decision support summary.** END the brief with:

```
THE MATH SAYS:
  Highest Y1: Verkada ($284K)
  Highest 3-YR upside: Verkada ($850K @ +10% RSU)
  Lowest variance: Cox-style (4-yr even vest, public co)
  Deadline pressure: Cox-style (Apr 30 — 5 days)

NEXT
  → Pick a counter to send first (deadline-driven)
  → /coin track <role_id> negotiating (after counter sent)
  → Accept: /coin track <role_id> offer-accepted
```

**Coin does NOT recommend a specific offer.** Surface the math and the trade-offs.

### Step 4 — Add safety guards

The mode must explicitly REFUSE:

| Refusal | Why |
|---|---|
| Auto-recommending one offer | Decision support, not advocacy |
| Auto-accepting or auto-declining | Real-world commitment — human gate |
| Inventing leverage points (FAANG tour, CS degree, named accounts) | Truthfulness gate |
| Computing taxes as advice | Approximation only — Sean confirms with a CPA on actual numbers |
| Drafting an aggressive counter without a real anchor | "Anchor must be a real competing offer or a clear PROFILE proof point" |

### Step 5 — Test

Add `tests/test_offer_math.py`:
1. `vest_share_y1` — assert 25/25/25/25 → 0.25; 5/15/40/40 → 0.05; cliff_months=18 → 0.0
2. `year_one_tc` — given a fixture offer, assert each component matches expected to within $1
3. `three_year_tc` — assert total under +10% growth > total under 0% > total under -20%
4. `historical_hit_rate` — empty list → 1.0; ["100%","85%","120%"] → ~1.017
5. `state_tax_rate` — UT=0.0465; unknown state defaults to 0.0 with no error
6. `delta_table` — first offer is baseline=true; deltas are signed integers

Add `tests/test_ofertas_mode.py`:
1. Read `modes/ofertas.md`
2. Assert each step (3.1–3.6) is present
3. Assert all 5 refusals from Step 4 are documented
4. Assert "never recommend a specific offer" appears
5. Assert "human gate" for accept/decline is explicit
6. Migration smoke: run `migrations/002_offers_table.py` against temp DB, assert table exists with all expected columns

### Step 6 — SKILL.md + _shared.md routing

`SKILL.md` — add to Mode Routing:
```
| `ofertas` or `offers` or `compare offers` | `modes/ofertas.md` (multi-offer math + negotiation brief) |
```

`SKILL.md` — add to Discovery menu:
```
  /coin ofertas               Compare 2+ offers + draft counters
```

`modes/_shared.md` — add to mode catalog:
```
| `ofertas` | Compare offers + negotiation counter-brief | `modes/ofertas.md` |
```

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/test_offer_math.py tests/test_ofertas_mode.py -v --tb=short
.venv/bin/python scripts/migrations/002_offers_table.py
.venv/bin/python -c "
from careerops.offer_math import year_one_tc, three_year_tc, vest_share_y1
o = {
    'base_salary': 185000, 'signing_bonus': 25000,
    'annual_bonus_target_pct': 0.15, 'annual_bonus_paid_history': '[\"100%\",\"100%\"]',
    'rsu_total_value': 120000, 'rsu_vesting_schedule': '25/25/25/25',
    'rsu_vest_years': 4, 'rsu_cliff_months': 12, 'state_tax': 'UT',
}
print(year_one_tc(o))
print(three_year_tc(o, rsu_growth_pct=0.10))
"
```

- [ ] `modes/ofertas.md` exists, follows the step shape
- [ ] `careerops/offer_math.py` math is correct against hand-calculated fixtures
- [ ] All 5 Step 4 refusals are explicit
- [ ] Tax rates are clearly labeled "approximation, not advice"
- [ ] Mode never auto-accepts / auto-declines / auto-recommends

## Definition of Done

- [ ] `modes/ofertas.md` authored
- [ ] `careerops/offer_math.py` exists with full function set
- [ ] Migration applied + tracked in `schema_migrations`
- [ ] Smoke run on a 2-offer fixture produces a clean comparison table
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/ofertas.md tests/test_ofertas_mode.py tests/test_offer_math.py
rm careerops/offer_math.py scripts/migrations/002_offers_table.py
git checkout .claude/skills/coin/SKILL.md modes/_shared.md docs/state/project-state.md
.venv/bin/python -c "
import sqlite3
db = sqlite3.connect('data/db/pipeline.db')
db.execute('DROP TABLE IF EXISTS offers')
db.execute('DELETE FROM schema_migrations WHERE name=\"002_offers_table\"')
db.commit()
"
```

## Notes for the executor

- This mode is decision support, NOT financial advice. Tax math is an approximation — bake that disclaimer into the output.
- The `rsu_growth_pct` sensitivity knob is critical — equity is the largest variance source in modern offers and Sean has been burned by paper RSU before. Always show 3 scenarios: -20%, 0%, +10%.
- Vesting schedule parsing should fail loudly on unknown formats — better to ask Sean than guess.
- For the negotiation brief: the strongest counter-anchor is almost always *a competing offer*. If only one offer exists, mode should print "Need another offer or a market-comp citation as anchor before drafting a counter" and stop the counter-brief step.
- The mode does not need browser MCP — pure terminal interaction with AskUserQuestion + Bash + Python.
