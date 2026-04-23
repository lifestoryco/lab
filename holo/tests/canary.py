"""Scraper drift canary.

Runs fetch_sales() against a handful of liquid, well-known cards and
asserts the result shape + price distribution is within a ±50% fence
of a committed baseline. Any deviation fails the pytest run loudly —
catches DOM renames, API schema drift, and unit-scale bugs.

Usage
-----
Offline lint (fast, no network):
    pytest tests/canary.py -q -k "drift"

Live canary (slow, hits PriceCharting + eBay):
    pytest tests/canary.py -q -m canary --run-canary

To update the baseline after a legitimate upstream change:
    python -m tests.canary --update-baseline
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from statistics import median

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASELINE_PATH = Path(__file__).resolve().parents[1] / "data" / "canary_baseline.json"

CANARY_CARDS = [
    {"card": "Charizard VMAX 20", "grade": "raw"},
    {"card": "Pikachu 58", "grade": "raw"},
    {"card": "Umbreon VMAX 215", "grade": "raw"},
    {"card": "Giratina V 186", "grade": "raw"},
    {"card": "Mew VMAX 114", "grade": "raw"},
]

DRIFT_TOLERANCE = 0.50  # ±50% from baseline median
MIN_SALES = 5


def _detect_drift(baseline: float, observed: float, tolerance: float = DRIFT_TOLERANCE) -> bool:
    """Return True when observed is outside ±tolerance of baseline."""
    if baseline <= 0:
        return False
    delta = abs(observed - baseline) / baseline
    return delta > tolerance


def _load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {}
    with BASELINE_PATH.open() as f:
        return json.load(f)


def _write_baseline(data: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BASELINE_PATH.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def _ewma(old: float, observed: float, alpha: float = 0.3) -> float:
    """Exponentially weighted moving average — resists single-day noise."""
    return round((1 - alpha) * old + alpha * observed, 2)


# --- offline tests -----------------------------------------------------------


def test_drift_detector_flags_large_delta():
    assert _detect_drift(100.0, 40.0) is True   # 60% below
    assert _detect_drift(100.0, 180.0) is True  # 80% above


def test_drift_detector_passes_small_delta():
    assert _detect_drift(100.0, 60.0) is False  # exactly 40%, within fence
    assert _detect_drift(100.0, 105.0) is False


def test_drift_detector_zero_baseline_never_drifts():
    # No baseline yet (first run) — can't assert drift
    assert _detect_drift(0.0, 9999.0) is False


def test_ewma_smooths_single_day_noise():
    smoothed = _ewma(100.0, 200.0, alpha=0.3)
    # 0.7*100 + 0.3*200 = 130 — one big day shifts the baseline but doesn't overwrite it
    assert smoothed == 130.0


# --- live canary (opt-in) ----------------------------------------------------


def _run_canary_required() -> bool:
    return os.environ.get("HOLO_RUN_CANARY", "0") == "1"


@pytest.mark.canary
@pytest.mark.skipif(not _run_canary_required(), reason="Set HOLO_RUN_CANARY=1 to run live canary")
@pytest.mark.parametrize("target", CANARY_CARDS, ids=lambda t: t["card"])
def test_live_canary(target: dict):
    from pokequant.scraper import fetch_sales

    sales = fetch_sales(target["card"], days=30, grade=target["grade"], use_cache=False)
    assert isinstance(sales, list), f"fetch_sales returned error envelope: {sales}"
    assert len(sales) >= MIN_SALES, f"{target['card']}: only {len(sales)} sales (need ≥{MIN_SALES})"

    sources = {s.get("source") for s in sales}
    assert "pricecharting" in sources or "ebay" in sources, (
        f"{target['card']}: no PC or eBay sales — scraper path may be broken. "
        f"Sources seen: {sources}"
    )

    baseline = _load_baseline().get(target["card"])
    if baseline:
        observed_median = float(median(s["price"] for s in sales))
        assert not _detect_drift(baseline["median"], observed_median), (
            f"{target['card']}: median ${observed_median:.2f} drifted >{int(DRIFT_TOLERANCE*100)}% "
            f"from baseline ${baseline['median']:.2f}"
        )


def _update_baseline_cli() -> int:
    """Run canary fetches and update data/canary_baseline.json via EWMA."""
    from pokequant.scraper import fetch_sales

    baseline = _load_baseline()
    for target in CANARY_CARDS:
        sales = fetch_sales(target["card"], days=30, grade=target["grade"], use_cache=False)
        if not isinstance(sales, list) or len(sales) < MIN_SALES:
            print(f"skip {target['card']}: insufficient data")
            continue
        observed = float(median(s["price"] for s in sales))
        prev = baseline.get(target["card"], {}).get("median", observed)
        baseline[target["card"]] = {
            "median": _ewma(prev, observed),
            "count": len(sales),
        }
        print(f"{target['card']}: median ${observed:.2f} → baseline ${baseline[target['card']]['median']:.2f}")
    _write_baseline(baseline)
    return 0


if __name__ == "__main__":
    if "--update-baseline" in sys.argv:
        sys.exit(_update_baseline_cli())
    print("Run with --update-baseline to seed data/canary_baseline.json")
    sys.exit(1)
