"""Tests for pokequant/ingestion/normalizer.py (Module 1)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from pokequant.ingestion.normalizer import (
    apply_iqr_filter,
    extract_raw_dataframe,
    ingest_card,
    normalize,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card_record(
    sales: list[dict] | None = None,
    card_id: str = "test_card",
    name: str = "Test Card",
    set_name: str = "Test Set",
) -> dict:
    """Build a minimal card record for ``extract_raw_dataframe``."""
    if sales is None:
        today = datetime.utcnow().date()
        sales = [
            {
                "sale_id": f"s_{i}",
                "price": 10.0 + i,
                "date": (today - timedelta(days=9 - i)).isoformat(),
                "condition": "NM",
                "source": "pricecharting",
                "quantity": 1,
            }
            for i in range(10)
        ]
    return {"card_id": card_id, "name": name, "set": set_name, "sales": sales}


# ---------------------------------------------------------------------------
# extract_raw_dataframe
# ---------------------------------------------------------------------------


def test_extract_raw_dataframe_valid():
    """Happy path — 10 sales should produce a 10-row DataFrame."""
    record = _make_card_record()
    df = extract_raw_dataframe(record)
    assert len(df) == 10
    assert "price" in df.columns
    assert "date" in df.columns
    assert "sale_id" in df.columns


def test_extract_raw_dataframe_missing_card_id():
    """Missing ``card_id`` key raises KeyError."""
    record = {"name": "X", "sales": []}
    with pytest.raises(KeyError, match="card_id"):
        extract_raw_dataframe(record)


def test_extract_raw_dataframe_missing_sales_key():
    """Missing ``sales`` key raises KeyError."""
    record = {"card_id": "x", "name": "X"}
    with pytest.raises(KeyError, match="sales"):
        extract_raw_dataframe(record)


# ---------------------------------------------------------------------------
# apply_iqr_filter
# ---------------------------------------------------------------------------


def test_apply_iqr_filter_removes_outliers():
    """A $999 outlier injected into a ~$10 dataset should be removed."""
    record = _make_card_record()
    df = extract_raw_dataframe(record)
    # Inject an extreme outlier.
    outlier = df.iloc[0:1].copy()
    outlier["price"] = 999.0
    outlier["sale_id"] = "outlier_1"
    df = pd.concat([df, outlier], ignore_index=True)
    assert len(df) == 11

    filtered = apply_iqr_filter(df)
    assert 999.0 not in filtered["price"].values
    assert len(filtered) < 11


def test_apply_iqr_filter_skips_iqr_on_small_dataset():
    """3 rows → skips IQR step (insufficient data), returns all 3."""
    today = datetime.utcnow().date()
    sales = [
        {
            "sale_id": f"s_{i}",
            "price": 10.0 + i,
            "date": (today - timedelta(days=i)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        }
        for i in range(3)
    ]
    df = extract_raw_dataframe(_make_card_record(sales=sales))
    filtered = apply_iqr_filter(df)
    assert len(filtered) == 3


def test_apply_iqr_filter_raises_on_empty():
    """All prices outside hard bounds → ValueError."""
    today = datetime.utcnow().date()
    sales = [
        {
            "sale_id": f"s_{i}",
            "price": 0.001,  # Below HARD_PRICE_FLOOR of 0.01
            "date": (today - timedelta(days=i)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        }
        for i in range(5)
    ]
    df = extract_raw_dataframe(_make_card_record(sales=sales))
    with pytest.raises(ValueError, match="[Aa]ll records"):
        apply_iqr_filter(df)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


def test_normalize_sorts_ascending_and_dedupes():
    """Out-of-order dates → sorted; duplicate sale_id → deduped."""
    today = datetime.utcnow().date()
    sales = [
        {
            "sale_id": "dup",
            "price": 10.0,
            "date": (today - timedelta(days=5)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        },
        {
            "sale_id": "dup",
            "price": 11.0,
            "date": (today - timedelta(days=3)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        },
        {
            "sale_id": "unique_1",
            "price": 12.0,
            "date": (today - timedelta(days=1)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        },
        {
            "sale_id": "unique_2",
            "price": 9.0,
            "date": (today - timedelta(days=7)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        },
    ]
    df = extract_raw_dataframe(_make_card_record(sales=sales))
    normed = normalize(df)
    # Duplicate removed.
    assert len(normed) == 3
    # Sorted ascending.
    dates = normed["date"].tolist()
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Timezone handling (Step 4)
# ---------------------------------------------------------------------------


def test_extract_raw_dataframe_mixed_tz_dates():
    """One UTC date string and one offset-aware date string parse without error."""
    sales = [
        {
            "sale_id": "tz_1",
            "price": 10.0,
            "date": "2024-04-12",  # Naive (treated as UTC)
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        },
        {
            "sale_id": "tz_2",
            "price": 11.0,
            "date": "2024-04-12T23:00:00-07:00",  # Pacific time
            "condition": "NM",
            "source": "tcgplayer",
            "quantity": 1,
        },
    ]
    record = _make_card_record(sales=sales)
    df = extract_raw_dataframe(record)
    assert len(df) == 2
    # Both dates should be tz-aware (UTC).
    assert df["date"].dt.tz is not None
