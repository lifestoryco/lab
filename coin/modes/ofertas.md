# Coin Mode — `ofertas` (multi-offer comparison + negotiation brief)

> Load `modes/_shared.md` first.

**Purpose:** When 2+ offers are active, compute Y1 and 3-yr TC under each
offer's vesting curve, surface side-by-side deltas, and draft per-offer
negotiation counters. **Decision support, not advocacy** — Coin presents
the math; Sean picks.

This is a port of the `santifer/career-ops` ofertas pattern.

---

## Hard refusals (read first)

| Refusal | Why |
|---|---|
| Recommending a specific offer ("you should take Verkada") | Decision support, not advocacy — surface trade-offs only |
| Auto-setting `status='offer-accepted'` or `'declined'` | Real-world commitment — human gate |
| Inventing leverage points (FAANG tour, CS degree, named accounts not in PROFILE) | Truthfulness gate (see `_shared.md` Operating Principle #3) |
| Presenting tax math as advice | Approximation only — Sean confirms with a CPA on actual numbers |
| Drafting an aggressive counter without a real anchor | Anchor must be a competing offer or a clear PROFILE proof point — never bluff |

---

## Step 0 — Load the AskUserQuestion tool

`AskUserQuestion` is a deferred tool. At mode entry, run:

```
ToolSearch(query="select:AskUserQuestion", max_results=1)
```

Without this, none of the per-offer questions in Step 2 can fire.

---

## Step 1 — Discover existing offers

Run:

```bash
.venv/bin/python -c "
from careerops.pipeline import list_roles
import json
rows = list_roles(status='offer', limit=20)
print(json.dumps([{'id': r['id'], 'company': r['company'], 'title': r['title']} for r in rows], indent=2))
"
```

If 0 rows, ask Sean: *"No roles in pipeline have status='offer'. Want to enter offers manually for comparison? (y/n)"*

If yes, walk Step 2 for each offer Sean wants to compare.
If no, exit cleanly.

---

## Step 2 — Capture offer details (per offer)

Use AskUserQuestion blocks (loaded in Step 0). For each offer, capture in this order:

1. **Company + title** (free-text, or auto-fill from `roles` row if `--from-role <id>`)
2. **Base salary** (free-text → integer USD, annualized)
3. **Signing bonus** (free-text → integer USD; default 0)
4. **Annual bonus target %** (free-text → float; e.g. "15" → 0.15)
5. **Historical bonus payout** (free-text — "team paid 100% last 2 years"; parse to JSON list `["100%", "100%"]`)
6. **RSU 4-yr grant value** (free-text → integer USD)
7. **Vesting schedule** — AskUserQuestion (single-select):
   - "25/25/25/25 — even 4-yr"
   - "5/15/40/40 — back-loaded"
   - "10/20/30/40 — graduated"
   - "6.25/q — quarterly even (after cliff)"
   - "Custom (free-text)"
8. **Cliff** — AskUserQuestion (single-select):
   - "None"
   - "6 months"
   - "12 months"
   - "Custom (free-text)"
9. **Remote %** — AskUserQuestion (single-select): 0 / 50 / 100
10. **State (for tax)** — free-text; default "UT" if remote_pct == 100
11. **Growth signal** — free-text (Series B, public, IPO 12mo, etc.)
12. **Offer expiration** — free-text date (YYYY-MM-DD); blank if none

Persist via:

```bash
.venv/bin/python -c "
from careerops.pipeline import insert_offer
oid = insert_offer({
    'role_id': <id or None>,
    'company': '...', 'title': '...',
    'received_at': '2026-04-25', 'expires_at': '...',
    'base_salary': 185000, 'signing_bonus': 25000,
    'annual_bonus_target_pct': 0.15,
    'annual_bonus_paid_history': '[\"100%\",\"100%\"]',
    'rsu_total_value': 120000,
    'rsu_vesting_schedule': '25/25/25/25',
    'rsu_vest_years': 4, 'rsu_cliff_months': 12,
    'remote_pct': 100, 'state_tax': 'UT',
    'growth_signal': '...', 'notes': '...',
})
print('inserted offer', oid)
"
```

---

## Step 3 — Compute the comparison

For each captured offer, compute:

```bash
.venv/bin/python -c "
from careerops.offer_math import year_one_tc, three_year_tc, delta_table
from careerops.pipeline import list_offers
offers = list_offers(status='active')
for o in offers:
    print(o['company'], year_one_tc(o), three_year_tc(o, rsu_growth_pct=0))
print('DELTAS:', delta_table(offers))
print('UPSIDE +10%:', [(o['company'], three_year_tc(o, rsu_growth_pct=10)) for o in offers])
print('DOWNSIDE -20%:', [(o['company'], three_year_tc(o, rsu_growth_pct=-20)) for o in offers])
"
```

Render as a side-by-side table to Sean — one column per offer:

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

---

## Step 4 — Per-offer narrative

For each offer, surface in plain English:

- **Strongest argument FOR it** — the dimension where this offer wins
  (highest base / largest signing / most aggressive RSU upside / cleanest remote).
- **Biggest risk** — concrete: "12-mo cliff + Series B = $0 in Y1 if you leave
  before month 13"; "75% of TC is RSU on a private co — illiquid until IPO".
- **Deadline pressure** — if `expires_at` within 7 days, flag in red.

---

## Step 5 — Negotiation counter-brief (per non-baseline offer)

For each offer that is NOT the highest Y1 TC, draft a counter:

```
Counter for <Company> ($229K Y1 vs <Anchor Company> $284K):

Anchor: <Anchor Company>'s $284K Y1 with 100% remote.
Ask: Bump base from $172K → $185K and add $25K signing.
Justification (pick what's true from PROFILE):
  - 15+ yr in <archetype-relevant domain> (<actual proof point from base.py>)
  - PMP + MBA
  - Local hire (no relocation cost) — if applicable
Concession lever: accept hybrid SLC if base hits $185K.
Best alternative: walk to <Anchor Company> — cleaner remote, larger Y1 TC.
```

**Hard rules for the counter:**

- Justifications MUST reference real PROFILE proof points (load
  `data/resumes/base.py` PROFILE before drafting).
- Never claim Cox/TitanX/Safeguard outcomes as direct employment — Sean was
  Hydrant's PM/COO on those engagements.
- If only one offer exists, print: *"Need another offer or a market-comp
  citation as anchor before drafting a counter — Coin will not bluff."* and
  STOP the counter step.

---

## Step 6 — Decision support summary

End the brief with:

```
THE MATH SAYS:
  Highest Y1: <co> ($XXXK)
  Highest 3-YR upside: <co> ($XXXK @ +10% RSU)
  Lowest variance: <co> (4-yr even vest, public co)
  Deadline pressure: <co> (Apr 30 — 5 days)

NEXT
  → Pick a counter to send first (deadline-driven)
  → Update offer in DB if you accept a counter
  → /coin track <role_id> negotiating  (after counter sent)
  → Accept: /coin track <role_id> offer-accepted   (human gate — Sean confirms)
  → Decline: /coin track <role_id> withdrawn
```

**Coin does NOT recommend a specific offer.** Surface the math and the trade-offs.

---

## Step 7 — Disclaimer (every run)

Print at the bottom:

```
ℹ️  Tax math is approximation, not advice. Confirm with a CPA on actual numbers.
ℹ️  RSU upside assumes the company you don't yet work at performs as projected.
   Treat -20% / 0% / +10% as bracketing scenarios, not predictions.
```

---

## Reference: `careerops/offer_math.py`

| Function | Returns |
|---|---|
| `year_one_tc(offer)` | dict — base, signing, rsu_y1, bonus_y1, total, effective_after_state_tax |
| `three_year_tc(offer, rsu_growth_pct=0)` | dict — base_total, signing, rsu_total_3yr, bonus_total, total |
| `vest_share_y1(offer)` | float — fraction of grant vesting Y1 (cliff-aware) |
| `vest_curve(offer)` | list[float] — per-year vest fractions, length = rsu_vest_years |
| `historical_hit_rate(offer)` | float — average of `annual_bonus_paid_history` (default 1.0) |
| `state_tax_rate(state_code)` | float — top-marginal approximation; unknown → 0.0 |
| `delta_table(offers)` | list[dict] — first offer is baseline |
