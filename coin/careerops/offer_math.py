"""Pure-Python offer comparison math.

No I/O. Functions accept dicts (matching the `offers` table row shape) so
they're callable from mode bash one-liners and easy to unit-test.

Tax math is APPROXIMATION ONLY. Surface as such — never present as advice.
Sean confirms with a CPA on real numbers.

Economic constants live in `config.py`:
  STATE_TAX_RATES    — top-marginal flat-equivalent state income tax
  ANNUAL_BASE_BUMP   — assumed annual base-salary growth multiplier
  DEFAULT_VEST_SCHEDULE — fallback when an offer leaves rsu_vesting_schedule blank
"""

from __future__ import annotations

import json
from typing import Iterable, TypedDict

from config import ANNUAL_BASE_BUMP, DEFAULT_VEST_SCHEDULE, STATE_TAX_RATES


class DeltaRow(TypedDict):
    """Shape of one row in the delta_table return value."""

    company: str | None
    title: str | None
    baseline: bool
    y1_total: int
    y1_after_tax: int
    y3_total: int
    delta_y1_vs_baseline: int


def state_tax_rate(state_code: str | None) -> float:
    """Return state income tax rate. Unknown / None → 0.0 (no error)."""
    if not state_code:
        return 0.0
    return STATE_TAX_RATES.get(state_code.upper().strip(), 0.0)


def _safe_vest_years(offer: dict) -> int:
    """Coerce rsu_vest_years to a sane positive integer (default 4)."""
    raw = offer.get("rsu_vest_years")
    try:
        years = int(raw) if raw is not None else 4
    except (TypeError, ValueError):
        years = 4
    return years if years >= 1 else 4


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
        # Default schedule from config (e.g. 25/25/25/25)
        schedule = DEFAULT_VEST_SCHEDULE
    if schedule.endswith("/q"):
        # Quarterly: '6.25/q' means 6.25% per quarter × 4 quarters
        try:
            per_q = float(schedule[:-2].strip())
            return round(per_q * 4 / 100.0, 4)
        except ValueError:
            return 0.25
    parts = [p.strip() for p in schedule.split("/")]
    try:
        first = float(parts[0])
        return round(first / 100.0, 4)
    except (ValueError, IndexError):
        return 0.25


def vest_curve(offer: dict) -> list[float]:
    """Return list of per-year vest fractions matching the schedule.

    Always length-padded to `rsu_vest_years` (minimum 1, default 4). Cliff > 12
    zeros Y1 and adds the missed share to Y2 (graded post-cliff catch-up)."""
    years = _safe_vest_years(offer)
    cliff = int(offer.get("rsu_cliff_months") or 0)
    schedule = (offer.get("rsu_vesting_schedule") or "").strip()
    if not schedule:
        schedule = DEFAULT_VEST_SCHEDULE
    if schedule.endswith("/q"):
        try:
            per_q = float(schedule[:-2].strip()) / 100.0
        except ValueError:
            per_q = 0.0625
        curve = [per_q * 4] * years
    else:
        try:
            curve = [float(p.strip()) / 100.0 for p in schedule.split("/") if p.strip()]
        except ValueError:
            curve = [1.0 / years] * years
    if not curve:
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

    Convention: Y1 RSU is valued at grant FMV (growth^0 — too volatile to
    project optimistically in Y1). Y2 vest event sits one year past the grant
    so applies (1 + growth)^1; Y3 vest sits two years past so (1 + growth)^2.
    Base bumps follow ANNUAL_BASE_BUMP^y for y in {0, 1, 2} (Y1, Y2, Y3).
    """
    base = int(offer.get("base_salary") or 0)
    signing = int(offer.get("signing_bonus") or 0)
    rsu_total = int(offer.get("rsu_total_value") or 0)
    bonus_target_pct = float(offer.get("annual_bonus_target_pct") or 0)
    hit_rate = historical_hit_rate(offer)
    curve = vest_curve(offer)
    growth = rsu_growth_pct / 100.0

    base_total = sum(int(round(base * (ANNUAL_BASE_BUMP ** y))) for y in range(3))
    bonus_total = sum(
        int(round(base * (ANNUAL_BASE_BUMP ** y) * bonus_target_pct * hit_rate))
        for y in range(3)
    )
    # RSU growth exponents track years-since-grant for each vest event:
    # Y1 vest = grant FMV (^0), Y2 vest = ^1, Y3 vest = ^2.
    rsu_y1_value = int(round(rsu_total * curve[0])) if len(curve) > 0 else 0
    rsu_y2_value = (
        int(round(rsu_total * curve[1] * (1 + growth) ** 1)) if len(curve) > 1 else 0
    )
    rsu_y3_value = (
        int(round(rsu_total * curve[2] * (1 + growth) ** 2)) if len(curve) > 2 else 0
    )
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


def delta_table(offers: Iterable[dict]) -> list[DeltaRow]:
    """Pairwise deltas vs the first offer (baseline)."""
    rows = list(offers)
    if not rows:
        return []
    baseline = year_one_tc(rows[0])["total"]
    out: list[DeltaRow] = []
    for i, o in enumerate(rows):
        y1 = year_one_tc(o)
        y3 = three_year_tc(o)
        out.append(DeltaRow(
            company=o.get("company"),
            title=o.get("title"),
            baseline=(i == 0),
            y1_total=y1["total"],
            y1_after_tax=y1["effective_after_state_tax"],
            y3_total=y3["total"],
            delta_y1_vs_baseline=y1["total"] - baseline,
        ))
    return out
