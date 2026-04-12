"""Shared fixtures for PokeQuant test suite."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest


@pytest.fixture
def minimal_sales_df() -> pd.DataFrame:
    """A 10-row sales DataFrame with all required columns."""
    base_date = datetime(2024, 3, 1)
    rows = []
    for i in range(10):
        rows.append({
            "sale_id": f"test_{i:03d}",
            "card_id": "test_card",
            "card_name": "Test Card",
            "set_name": "Test Set",
            "language": "EN",
            "price": 10.0 + i * 0.5,
            "date": pd.Timestamp(base_date + timedelta(days=i)),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_box_data() -> dict:
    """A valid box_data dict for calculate_box_ev()."""
    return {
        "set_name": "Test Set",
        "packs_per_box": 36,
        "retail_price": 149.99,
        "pull_rates": {
            "Secret Rare": {
                "rate": "1/36",
                "cards": [
                    {"name": "Big Hit", "market_value": 120.00},
                    {"name": "Medium Hit", "market_value": 40.00},
                ],
            },
            "Ultra Rare": {
                "rate": "1/6",
                "cards": [
                    {"name": "Chase Card", "market_value": 15.00},
                    {"name": "Decent Pull", "market_value": 8.00},
                ],
            },
        },
    }


@pytest.fixture
def sample_inventory() -> dict:
    """Standard bulk inventory for testing."""
    return {"Common": 500, "Uncommon": 200, "Reverse Holo": 50}


@pytest.fixture
def sample_sales_list() -> list[dict]:
    """A list of 12 sale dicts in the scraper output format."""
    base_date = datetime(2024, 3, 1)
    return [
        {
            "sale_id": f"sale_{i:03d}",
            "price": round(25.0 + (i % 5) * 2.0 - (i % 3) * 1.0, 2),
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": 1,
        }
        for i in range(12)
    ]
