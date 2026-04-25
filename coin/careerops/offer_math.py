"""Pure-Python offer comparison math.

No I/O. Functions accept dicts (matching the `offers` table row shape) so
they're callable from mode bash one-liners and easy to unit-test.

Tax math is APPROXIMATION ONLY. Surface as such — never present as advice.
Uses 2024 top marginal flat-equivalent rates for the most common states for
remote workers. Sean confirms with a CPA on real numbers.
"""

from __future__ import annotations

import json
from typing import Iterable


# State income tax (top marginal / flat-equivalent). Approximation.
_STATE_TAX = {
    "CA": 0.093,
    "NY": 0.0685,
    "OR": 0.099,
    "MN": 0.0985,
    "NJ": 0.0897,
    "MA": 0.05,
    "CO": 0.0444,
    "UT": 0.0465,
    "ID": 0.058,
    "AZ": 0.025,
    "WA": 0.0,
    "TX": 0.0,
    "FL": 0.0,
    "NV": 0.0,
    "TN": 0.0,
    "WY": 0.0,
    "SD": 0.0,
    "AK": 0.0,
    "NH": 0.0,
}


def state_tax_rate(state_code: str | None) -> float:
    """Return state income tax rate. Unknown / None → 0.0 (no error)."""
    if not state_code:
        return 0.0
    return _STATE_TAX.get(state_code.upper().strip(), 0.0)


def vest_share_y1(offer: dict) -> float:
    """Fraction of total RSU grant vesting in year 1.

    Honors `rsu_cliff_months`: cliff > 12 → 0.0 in Y1.
    Parses common `rsu_vesting_schedule` strings:
      '25/25/25/25'    → 0.25  (4-yr even)
      '5/15/40/40'     → 0.05  (back-loaded)
      '10/20/30/40'    → 0.10
      '6.25/q'         → 0.25  (quarterly even = 6.25% × 4)
      '0/33/33/34'     → 0.0   (1-yr cliff implicit)
    """
    cliff = int(offer.get("rsu_cliff_months") or 0)
    if cliff > 12:
        return 0.0
    schedule = (offer.get("rsu_vesting_schedule") or "").strip()
    if not schedule:
        # Default to 25/25/25/25 with 12-month cliff
        return 0.25
    if schedule.endswith("/q"):
        # Quarterly: '6.25/q' means 6.25% per quarter × 4 quarters
        try:
            per_q = float(schedule[:-2])
            return round(per_q * 4 / 100.0, 4)
        except ValueError:
            return 0.25
    parts = schedule.split("/")
    try:
        first = float(parts[0])
        return round(first / 100.0, 4)
    except (ValueError, IndexError):
        return 0.25


def vest_curve(offer: dict) -> list[float]:
    """Return list of per-year vest fractions matching the schedule.

    Always length-padded to `rsu_vest_years` (default 4). Cliff > 12 zeros Y1
    and adds the missed share to Y2 (graded post-cliff catch-up)."""
    years = int(offer.get("rsu_vest_years") or 4)
    cliff = int(offer.get("rsu_cliff_months") or 0)
    schedule = (offer.get("rsu_vesting_schedule") or "").strip()
    if not schedule:
        curve = [1.0 / years] * years
    elif schedule.endswith("/q"):
        try:
            per_q = float(schedule[:-2]) / 100.0
        except ValueError:
            per_q = 0.0625
        curve = [per_q * 4] * years
    else:
        try:
            curve = [float(p) / 100.0 for p in schedule.split("/")]
        except ValueError:
            curve = [1.0 / years] * years
    # Pad / truncate to `years`
    if len(curve) < years:
        curve = curve + [0.0] * (years - len(curve))
    elif len(curve) > years:
        curve = curve[:years]
    if cliff > 12 and len(curve) >= 2:
        moved = curve[0]
        curve[0] = 0.0
        curve[1] = curve[1] + moved
    return curve


def historical_hit_rate(offer: dict) -> float:
    """Average historical bonus payout as fraction of target. Default 1.0."""
    raw = offer.get("annual_bonus_paid_history")
    if not raw:
        return 1.0
    if isinstance(raw, str):
        try:
            history = json.loads(raw)
        except (ValueError, TypeError):
            return 1.0
    else:
        history = raw
    if not history:
        return 1.0
    rates: list[float] = []
    for item in history:
        s = str(item).strip().rstrip("%")
        try:
            rates.append(float(s) / 100.0)
        except ValueError:
            continue
    if not rates:
        return 1.0
    return round(sum(rates) / len(rates), 4)


def year_one_tc(offer: dict) -> dict:
    """Compute Y1 TC components + total + post-state-tax."""
    base = int(offer.get("base_salary") or 0)
    signing = int(offer.get("signing_bonus") or 0)
    rsu_total = int(offer.get("rsu_total_value") or 0)
    rsu_y1 = int(round(rsu_total * vest_share_y1(offer)))
    bonus_target_pct = float(offer.get("annual_bonus_target_pct") or 0)
    bonus_y1 = int(round(base * bonus_target_pct * historical_hit_rate(offer)))
    total = base + signing + rsu_y1 + bonus_y1
    rate = state_tax_rate(offer.get("state_tax"))
    after_tax = int(round(total * (1 - rate)))
    return {
        "base": base,
        "signing": signing,
        "rsu_y1": rsu_y1,
        "bonus_y1": bonus_y1,
        "total": total,
        "effective_after_state_tax": after_tax,
        "state_tax_rate": rate,
    }


def three_year_tc(offer: dict, rsu_growth_pct: float = 0.0) -> dict:
    """Compute 3-yr TC summed. `rsu_growth_pct` is sensitivity (0 = neutral,
    +10 = bullish, -20 = bearish) — applied to RSU vests Y2 and Y3.

    Year-1 RSU is valued at grant FMV (no growth applied — too volatile to
    project optimistically in Y1). Years 2 and 3 apply (1 + growth)^year.
    """
    base = int(offer.get("base_salary") or 0)
    signing = int(offer.get("signing_bonus") or 0)
    rsu_total = int(offer.get("rsu_total_value") or 0)
    bonus_target_pct = float(offer.get("annual_bonus_target_pct") or 0)
    hit_rate = historical_hit_rate(offer)
    curve = vest_curve(offer)
    growth = rsu_growth_pct / 100.0

    # 3-yr base — assume 4% annual base bumps (industry standard mid-tenure)
    base_total = sum(int(round(base * (1.04 ** y))) for y in range(3))
    bonus_total = sum(
        int(round(base * (1.04 ** y) * bonus_target_pct * hit_rate)) for y in range(3)
    )
    # RSU: Y1 at FMV, Y2/Y3 with sensitivity applied
    rsu_y1_value = int(round(rsu_total * curve[0])) if len(curve) > 0 else 0
    rsu_y2_value = int(round(rsu_total * curve[1] * (1 + growth) ** 2)) if len(curve) > 1 else 0
    rsu_y3_value = int(round(rsu_total * curve[2] * (1 + growth) ** 3)) if len(curve) > 2 else 0
    rsu_total_3yr = rsu_y1_value + rsu_y2_value + rsu_y3_value

    total = base_total + signing + bonus_total + rsu_total_3yr
    rate = state_tax_rate(offer.get("state_tax"))
    after_tax = int(round(total * (1 - rate)))
    return {
        "base_total": base_total,
        "signing": signing,
        "rsu_total_3yr": rsu_total_3yr,
        "bonus_total": bonus_total,
        "total": total,
        "effective_after_state_tax": after_tax,
        "rsu_growth_pct": rsu_growth_pct,
    }


def delta_table(offers: Iterable[dict]) -> list[dict]:
    """Pairwise deltas vs the first offer (baseline)."""
    rows = list(offers)
    if not rows:
        return []
    baseline = year_one_tc(rows[0])["total"]
    out: list[dict] = []
    for i, o in enumerate(rows):
        y1 = year_one_tc(o)
        y3 = three_year_tc(o)
        out.append({
            "company": o.get("company"),
            "title": o.get("title"),
            "baseline": i == 0,
            "y1_total": y1["total"],
            "y1_after_tax": y1["effective_after_state_tax"],
            "y3_total": y3["total"],
            "delta_y1_vs_baseline": y1["total"] - baseline,
        })
    return out
