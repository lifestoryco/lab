"""Tests for pokequant/comps/generator.py."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from pokequant.comps.generator import (
    _assess_confidence,
    _assign_decay_weights,
    SalePoint,
    generate_comp_from_list,
)
import pandas as pd


def _make_sales(n: int, base_price: float = 25.0) -> list[dict]:
    """Generate n sale dicts spread over consecutive days."""
    base_date = datetime(2024, 3, 1)
    return [
        {
            "sale_id": f"s{i}",
            "price": round(base_price + (i % 4) * 1.0, 2),
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "condition": "NM",
            "source": "pricecharting",
        }
        for i in range(n)
    ]


class TestGenerateCompFromList:
    def test_happy_path(self, sample_sales_list):
        """12 sales produce cmc, confidence, volatility_score — all populated."""
        result = generate_comp_from_list(
            sales=sample_sales_list,
            card_id="test_card",
            card_name="Test Card",
        )
        assert result.cmc > 0
        assert result.confidence in ("HIGH", "MEDIUM", "LOW")
        assert result.volatility_score in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")

    def test_empty_raises(self):
        """Empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            generate_comp_from_list(
                sales=[], card_id="test", card_name="Test"
            )

    def test_missing_key_raises(self):
        """Sale missing 'price' key raises KeyError."""
        bad_sales = [{"sale_id": "x", "date": "2024-01-01", "condition": "NM", "source": "pc"}]
        with pytest.raises(KeyError, match="price"):
            generate_comp_from_list(sales=bad_sales, card_id="test")

    def test_single_sale_volatility_unknown(self):
        """1 sale -> volatility_score == 'UNKNOWN', confidence == 'LOW', warning set."""
        sales = _make_sales(1)
        result = generate_comp_from_list(
            sales=sales, card_id="test", card_name="Test"
        )
        assert result.volatility_score == "UNKNOWN"
        assert result.confidence == "LOW"
        assert result.insufficient_data_warning != ""


class TestAssignDecayWeights:
    def test_newest_highest(self):
        """Weight at index 0 is always greater than weight at index 1."""
        points = [
            SalePoint(sale_id=f"s{i}", price=10.0, date=pd.Timestamp("2024-03-01"),
                      condition="NM", source="pc")
            for i in range(5)
        ]
        weighted = _assign_decay_weights(points, lam=0.3)
        assert weighted[0].weight > weighted[1].weight
        assert weighted[1].weight > weighted[2].weight


class TestAssessConfidence:
    def test_high(self):
        """8 sales, spread 7 days -> HIGH."""
        assert _assess_confidence(8, 7) == "HIGH"

    def test_low(self):
        """2 sales, spread 45 days -> LOW."""
        assert _assess_confidence(2, 45) == "LOW"
