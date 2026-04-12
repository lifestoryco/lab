"""Tests for pokequant/ingestion/normalizer.py."""

from __future__ import annotations

import pandas as pd
import pytest

from pokequant.ingestion.normalizer import (
    apply_iqr_filter,
    extract_raw_dataframe,
    normalize,
)


def _make_card_record(sales: list[dict], card_id: str = "test_card") -> dict:
    """Helper to build a minimal card record dict."""
    return {
        "card_id": card_id,
        "name": "Test Card",
        "set": "Test Set",
        "sales": sales,
    }


def _make_sale(
    sale_id: str = "s001",
    price: float = 10.0,
    date: str = "2024-03-01",
    **overrides,
) -> dict:
    """Helper to build a single sale dict."""
    sale = {
        "sale_id": sale_id,
        "price": price,
        "date": date,
        "condition": "NM",
        "source": "pricecharting",
        "quantity": 1,
    }
    sale.update(overrides)
    return sale


# -----------------------------------------------------------------------
# extract_raw_dataframe
# -----------------------------------------------------------------------


class TestExtractRawDataframe:
    def test_valid(self):
        """Happy path: 3 well-formed sales."""
        sales = [_make_sale(sale_id=f"s{i}", price=10.0 + i) for i in range(3)]
        record = _make_card_record(sales)
        df = extract_raw_dataframe(record)
        assert len(df) == 3
        assert "price" in df.columns
        assert "date" in df.columns
        assert df["card_id"].iloc[0] == "test_card"

    def test_missing_card_id(self):
        """Record missing 'card_id' raises KeyError."""
        record = {"name": "X", "sales": [_make_sale()]}
        with pytest.raises(KeyError, match="card_id"):
            extract_raw_dataframe(record)

    def test_missing_sales_key(self):
        """Record missing 'sales' key raises KeyError."""
        record = {"card_id": "x", "name": "X"}
        with pytest.raises(KeyError, match="sales"):
            extract_raw_dataframe(record)

    def test_mixed_tz_dates(self):
        """One UTC and one offset-aware date both parse without error."""
        sales = [
            _make_sale(sale_id="tz1", date="2024-03-01T12:00:00Z"),
            _make_sale(sale_id="tz2", date="2024-03-01T23:00:00-07:00"),
        ]
        record = _make_card_record(sales)
        df = extract_raw_dataframe(record)
        assert len(df) == 2
        # Both dates should be UTC-aware.
        assert df["date"].dt.tz is not None


# -----------------------------------------------------------------------
# apply_iqr_filter
# -----------------------------------------------------------------------


class TestApplyIqrFilter:
    def test_removes_outliers(self):
        """A $999 outlier injected into normal data is removed."""
        prices = [10.0, 11.0, 10.5, 12.0, 9.5, 10.8, 11.2, 999.0]
        df = pd.DataFrame({"price": prices})
        result = apply_iqr_filter(df)
        assert 999.0 not in result["price"].values
        assert len(result) < len(df)

    def test_skips_iqr_on_small_dataset(self):
        """3 rows should skip IQR step and return all 3."""
        df = pd.DataFrame({"price": [5.0, 10.0, 15.0]})
        result = apply_iqr_filter(df)
        assert len(result) == 3

    def test_raises_on_empty(self):
        """All prices outside hard bounds raises ValueError."""
        df = pd.DataFrame({"price": [0.001, 0.002, 0.003]})
        with pytest.raises(ValueError, match="removed"):
            apply_iqr_filter(df)


# -----------------------------------------------------------------------
# normalize
# -----------------------------------------------------------------------


class TestNormalize:
    def test_sorts_ascending_and_dedupes(self):
        """Out-of-order dates get sorted; duplicate sale_id is deduped."""
        df = pd.DataFrame({
            "sale_id": ["a", "b", "a"],
            "price": [10.0, 12.0, 10.0],
            "date": pd.to_datetime(["2024-03-03", "2024-03-01", "2024-03-03"]),
            "condition": ["NM", "NM", "NM"],
            "source": ["pc", "pc", "pc"],
            "quantity": [1, 1, 1],
        })
        result = normalize(df)
        # Should be deduped to 2 rows.
        assert len(result) == 2
        # Should be sorted ascending by date.
        dates = result["date"].tolist()
        assert dates[0] <= dates[1]
        # Should have price_usd alias.
        assert "price_usd" in result.columns
