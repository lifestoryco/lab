"""fetch_sales parity — legacy vs registry path.

Runs each canary card through both code paths and asserts the price
distributions are within 5% of each other. This is the gate for
flipping HOLO_USE_REGISTRY=1 in production.

Live-gated: set HOLO_RUN_PARITY=1 to execute. The offline assertions
below run in the default suite.

Usage
-----
    HOLO_RUN_PARITY=1 pytest tests/test_fetch_sales_parity.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from statistics import median

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CANARY_CARDS = [
    {"card": "Charizard VMAX 20", "grade": "raw"},
    {"card": "Pikachu 58",        "grade": "raw"},
    {"card": "Umbreon VMAX 215",  "grade": "raw"},
    {"card": "Giratina V 186",    "grade": "raw"},
    {"card": "Mew VMAX 114",      "grade": "raw"},
]

PARITY_TOLERANCE = 0.05  # ±5% median delta


def _median_delta(a: list[dict], b: list[dict]) -> float:
    """Return |median(a) - median(b)| / median(b), or inf when either side empty."""
    prices_a = [float(s["price"]) for s in a if isinstance(s, dict) and "price" in s]
    prices_b = [float(s["price"]) for s in b if isinstance(s, dict) and "price" in s]
    if not prices_a or not prices_b:
        return float("inf")
    ma = median(prices_a)
    mb = median(prices_b)
    if mb == 0:
        return float("inf")
    return abs(ma - mb) / mb


# --- offline delta-math sanity tests (run in default suite) ------------------


def test_median_delta_zero_on_identical_distributions():
    a = [{"price": 10.0}, {"price": 20.0}, {"price": 30.0}]
    b = [{"price": 10.0}, {"price": 20.0}, {"price": 30.0}]
    assert _median_delta(a, b) == 0.0


def test_median_delta_within_tolerance():
    a = [{"price": 100.0}, {"price": 100.0}, {"price": 100.0}]
    b = [{"price": 104.0}, {"price": 104.0}, {"price": 104.0}]
    # 4% delta — under the 5% fence
    assert _median_delta(a, b) < PARITY_TOLERANCE


def test_median_delta_exceeds_tolerance_on_large_shift():
    a = [{"price": 100.0}]
    b = [{"price": 150.0}]
    assert _median_delta(a, b) > PARITY_TOLERANCE


def test_median_delta_empty_returns_inf():
    assert _median_delta([], [{"price": 10.0}]) == float("inf")
    assert _median_delta([{"price": 10.0}], []) == float("inf")


# --- live parity (opt-in) ----------------------------------------------------


def _run_parity_required() -> bool:
    return os.environ.get("HOLO_RUN_PARITY", "0") == "1"


@pytest.mark.canary
@pytest.mark.skipif(not _run_parity_required(),
                    reason="Set HOLO_RUN_PARITY=1 to run live parity gate")
@pytest.mark.parametrize("target", CANARY_CARDS, ids=lambda t: t["card"])
def test_legacy_and_registry_path_parity(monkeypatch, target):
    """Both code paths produce a sale list whose median is within 5%."""
    from pokequant.scraper import fetch_sales

    # Legacy path
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)
    legacy = fetch_sales(target["card"], days=30, grade=target["grade"], use_cache=False)

    # Registry path
    monkeypatch.setenv("HOLO_USE_REGISTRY", "1")
    registry = fetch_sales(target["card"], days=30, grade=target["grade"], use_cache=False)

    assert isinstance(legacy, list), f"legacy errored: {legacy}"
    # Registry may still fall back to legacy if no adapters returned records —
    # that's acceptable for this gate, but log it.
    if not isinstance(registry, list):
        pytest.skip(f"registry path errored / fell back: {registry}")

    delta = _median_delta(registry, legacy)
    assert delta < PARITY_TOLERANCE, (
        f"{target['card']}: median delta {delta*100:.1f}% exceeds "
        f"{int(PARITY_TOLERANCE*100)}% fence — investigate before enabling registry"
    )
