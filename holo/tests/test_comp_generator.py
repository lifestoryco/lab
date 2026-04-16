"""Tests for pokequant/comps/generator.py (Module 5)."""

from __future__ import annotations

import pytest

from pokequant.comps.generator import (
    _assess_confidence,
    _assign_decay_weights,
    CompResult,
    SalePoint,
    generate_comp_from_list,
)


# ---------------------------------------------------------------------------
# generate_comp_from_list
# ---------------------------------------------------------------------------


def test_generate_comp_from_list_happy_path(sample_sales_list):
    """12 sales → cmc, confidence, volatility_score are all populated."""
    result = generate_comp_from_list(
        sales=sample_sales_list,
        card_id="test_card",
        card_name="Test Card",
    )
    assert isinstance(result.cmc, float)
    assert result.cmc > 0
    assert result.confidence in ("HIGH", "MEDIUM", "LOW")
    assert result.volatility_score in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    assert result.sales_used == 10  # COMP_SALES_LIMIT default


def test_generate_comp_from_list_empty_raises():
    """Empty list → ValueError."""
    with pytest.raises(ValueError, match="[Ee]mpty"):
        generate_comp_from_list(sales=[], card_id="x")


def test_generate_comp_from_list_missing_key_raises():
    """Sale missing ``price`` → KeyError."""
    bad_sales = [{"sale_id": "a", "date": "2024-01-01", "condition": "NM", "source": "x"}]
    with pytest.raises(KeyError, match="price"):
        generate_comp_from_list(sales=bad_sales, card_id="x")


def test_generate_comp_single_sale_volatility_unknown():
    """1 sale → volatility_score == \"UNKNOWN\", confidence == \"LOW\"."""
    single = [{
        "sale_id": "solo",
        "price": 25.0,
        "date": "2024-06-01",
        "condition": "NM",
        "source": "pricecharting",
    }]
    result = generate_comp_from_list(sales=single, card_id="solo_card")
    assert result.volatility_score == "UNKNOWN"
    assert result.confidence == "LOW"
    assert result.insufficient_data_warning != ""


# ---------------------------------------------------------------------------
# _assign_decay_weights
# ---------------------------------------------------------------------------


def test_assign_decay_weights_newest_highest():
    """Weight at index 0 > weight at index 1 (always, for λ > 0)."""
    import pandas as pd

    points = [
        SalePoint(sale_id=f"w{i}", price=10.0, date=pd.Timestamp("2024-01-01"),
                  condition="NM", source="test")
        for i in range(5)
    ]
    weighted = _assign_decay_weights(points, lam=0.3)
    assert weighted[0].weight > weighted[1].weight
    # Weights should be strictly decreasing.
    for i in range(len(weighted) - 1):
        assert weighted[i].weight > weighted[i + 1].weight


# ---------------------------------------------------------------------------
# _assess_confidence
# ---------------------------------------------------------------------------


def test_assess_confidence_high():
    """8 sales, spread 7 days → \"HIGH\"."""
    assert _assess_confidence(8, 7) == "HIGH"


def test_assess_confidence_low():
    """2 sales, spread 45 days → \"LOW\"."""
    assert _assess_confidence(2, 45) == "LOW"
