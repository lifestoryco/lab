"""Shared test fixtures for PokeQuant test suite."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# Ensure the project root is importable.
sys.path.insert(0, str(Path(__file__).parents[1]))


@pytest.fixture()
def minimal_sales_df() -> pd.DataFrame:
    """A 10-row sales DataFrame with all required columns."""
    today = datetime.utcnow().date()
    rows = []
    for i in range(10):
        rows.append({
            "sale_id": f"test_{i:03d}",
            "card_id": "test_card",
            "card_name": "Test Card",
            "set_name": "Test Set",
            "language": "EN",
            "price": 10.0 + i * 0.5,
            "date": pd.Timestamp(today - timedelta(days=9 - i), tz="UTC"),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        })
    return pd.DataFrame(rows)


@pytest.fixture()
def sample_box_data() -> dict:
    """A valid box_data dict for ``calculate_box_ev()``."""
    return {
        "set_name": "Test Set",
        "packs_per_box": 36,
        "retail_price": 149.99,
        "pull_rates": {
            "Secret Rare": {
                "rate": "1/36",
                "cards": [
                    {"name": "Chase Card A", "market_value": 120.00},
                    {"name": "Chase Card B", "market_value": 30.00},
                ],
            },
            "Ultra Rare": {
                "rate": "1/6",
                "cards": [
                    {"name": "Ultra A", "market_value": 8.00},
                    {"name": "Ultra B", "market_value": 5.00},
                ],
            },
        },
    }


@pytest.fixture()
def sample_inventory() -> dict[str, int]:
    """Bulk inventory for ``analyze_bulk_lot()``."""
    return {"Common": 500, "Uncommon": 200, "Reverse Holo": 50}


@pytest.fixture()
def sample_sales_list() -> list[dict]:
    """A list of 12 sale dicts in the scraper output format."""
    today = datetime.utcnow().date()
    return [
        {
            "sale_id": f"sl_{i:03d}",
            "price": 20.0 + (i % 5) * 2.0,
            "date": (today - timedelta(days=11 - i)).isoformat(),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        }
        for i in range(12)
    ]
