"""
tests/test_scraper.py
---------------------
Unit tests for pokequant/scraper.py — focusing on the new branches
introduced in the 2026-04-16 session:

  - eBay s-item / s-card selector fallback chain
  - s-item__title title extraction (2024+ DOM)
  - s-item__price range ("$4.00 to $6.00") → lower bound
  - 3-way sold-date fallback (s-item__ended-date / s-item__time-end / su-styled-text)
  - TCGPlayer sparse supplement grade-gate (raw only, not psa9/psa10)
  - TCGPlayer sparse supplement merges without duplicating existing dates
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is on sys.path so scraper can be imported.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Point cache at a temp location so tests never write to data/db/.
os.environ.setdefault("HOLO_CACHE_DB", "/tmp/holo_test_cache.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ebay_html(
    container_class: str = "s-item",
    title_class: str = "s-item__title",
    price_text: str = "$12.50",
    date_class: str = "s-item__ended-date",
    date_text: str = "Sold  Apr 8, 2026",
    title_text: str = "Charizard V NM Pokemon Card",
) -> str:
    """Build a minimal eBay completed-listings HTML fragment."""
    return dedent(f"""
        <html><body><ul>
          <li class="{container_class}">
            <div class="{title_class}">{title_text}</div>
            <span class="s-item__price">{price_text}</span>
            <span class="{date_class}">{date_text}</span>
          </li>
        </ul></body></html>
    """)


# ---------------------------------------------------------------------------
# eBay selector: s-item (2024+ DOM)
# ---------------------------------------------------------------------------

class TestEbaySelector:
    """eBay container selector falls back gracefully."""

    def _run_scrape(self, html: str, card_name: str = "Charizard V", days: int = 30):
        """Call _scrape_ebay with a mocked HTTP response."""
        from pokequant.scraper import _scrape_ebay

        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("pokequant.scraper._get", return_value=mock_resp):
            return _scrape_ebay(card_name, days=days)

    def test_s_item_container_parsed(self):
        """Standard 2024+ s-item container returns a sale record."""
        html = _make_ebay_html(container_class="s-item")
        sales = self._run_scrape(html)
        assert len(sales) == 1
        assert sales[0]["price"] == 12.50
        assert sales[0]["source"] == "ebay"

    def test_s_card_fallback_parsed(self):
        """Legacy s-card container is also accepted when s-item is absent."""
        html = _make_ebay_html(container_class="s-card")
        sales = self._run_scrape(html)
        assert len(sales) == 1
        assert sales[0]["price"] == 12.50

    def test_s_item_title_extraction(self):
        """Title is read from div.s-item__title, not just img alt."""
        html = _make_ebay_html(
            container_class="s-item",
            title_class="s-item__title",
            title_text="Umbreon VMAX NM",
        )
        sales = self._run_scrape(html, card_name="Umbreon VMAX")
        assert len(sales) == 1

    def test_shop_on_ebay_ad_skipped(self):
        """Promoted 'Shop on eBay' listings are filtered out."""
        html = _make_ebay_html(title_text="Shop on eBay")
        sales = self._run_scrape(html)
        assert sales == []

    def test_graded_listing_skipped(self):
        """PSA-graded listings are filtered out for raw queries."""
        html = _make_ebay_html(title_text="Charizard V PSA 10 Graded")
        sales = self._run_scrape(html)
        assert sales == []


# ---------------------------------------------------------------------------
# eBay price: range handling
# ---------------------------------------------------------------------------

class TestEbayPriceRange:
    """Price ranges like '$4.00 to $6.00' take the lower bound."""

    def _parse_price(self, price_text: str) -> float | None:
        """Run _scrape_ebay with a custom price string, return parsed price."""
        from pokequant.scraper import _scrape_ebay

        html = _make_ebay_html(price_text=price_text)
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("pokequant.scraper._get", return_value=mock_resp):
            sales = _scrape_ebay("Charizard V", days=30)

        return sales[0]["price"] if sales else None

    def test_single_price_parsed(self):
        assert self._parse_price("$12.50") == 12.50

    def test_range_lower_bound_taken(self):
        """'$4.00 to $6.00' → $4.00."""
        assert self._parse_price("$4.00 to $6.00") == 4.00

    def test_price_with_comma_parsed(self):
        """'$1,250.00' → 1250.00."""
        assert self._parse_price("$1,250.00") == 1250.00


# ---------------------------------------------------------------------------
# eBay date: 3-way fallback
# ---------------------------------------------------------------------------

class TestEbayDateFallback:
    """Sold date falls back through three class names in order."""

    def _get_date(self, date_class: str, date_text: str = "Apr 8, 2026") -> str | None:
        from pokequant.scraper import _scrape_ebay

        html = _make_ebay_html(date_class=date_class, date_text=date_text)
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("pokequant.scraper._get", return_value=mock_resp):
            sales = _scrape_ebay("Charizard V", days=365)

        return sales[0]["date"] if sales else None

    def test_s_item_ended_date(self):
        d = self._get_date("s-item__ended-date", "Apr 8, 2026")
        assert d == "2026-04-08"

    def test_s_item_time_end_fallback(self):
        d = self._get_date("s-item__time-end", "Apr 8, 2026")
        assert d == "2026-04-08"

    def test_su_styled_text_fallback(self):
        d = self._get_date("su-styled-text", "Sold  Apr 8, 2026")
        assert d == "2026-04-08"

    def test_missing_date_uses_today(self):
        """If no date span is found, the sale date defaults to UTC today."""
        from datetime import datetime
        from pokequant.scraper import _scrape_ebay

        html = dedent("""
            <html><body><ul>
              <li class="s-item">
                <div class="s-item__title">Charizard V NM</div>
                <span class="s-item__price">$12.50</span>
              </li>
            </ul></body></html>
        """)
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("pokequant.scraper._get", return_value=mock_resp):
            sales = _scrape_ebay("Charizard V", days=30)

        # Scraper uses datetime.utcnow().date() as fallback — match that.
        assert len(sales) == 1
        assert sales[0]["date"] == datetime.utcnow().date().isoformat()


# ---------------------------------------------------------------------------
# TCGPlayer sparse supplement — grade gate
# ---------------------------------------------------------------------------

class TestTcgPlayerSparseSupplementGradeGate:
    """Sparse supplement fires for raw grade only, not psa9/psa10."""

    def _run_fetch(
        self,
        grade: str,
        pc_sales_count: int = 5,
        days: int = 90,
    ) -> list[dict]:
        """
        Run fetch_sales with mocked PC returning pc_sales_count records
        and a mock TCGPlayer supplement that returns 3 extra records.
        Returns the final merged sales list.
        """
        from pokequant.scraper import fetch_sales

        today = date.today()
        pc_sales = [
            {
                "sale_id": f"pc_{i:03d}",
                "price": 20.0 + i,
                "date": (today - timedelta(days=i)).isoformat(),
                "condition": "NM",
                "source": "pricecharting",
                "quantity": 1,
            }
            for i in range(pc_sales_count)
        ]

        tcg_supplement = [
            {
                "sale_id": f"tcg_{i:03d}",
                "price": 18.0 + i,
                "date": (today - timedelta(days=100 + i)).isoformat(),
                "condition": "NM",
                "source": "tcgplayer",
                "quantity": 1,
            }
            for i in range(3)
        ]

        with (
            patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales),
            patch("pokequant.scraper._scrape_ebay", return_value=[]),
            patch("pokequant.scraper._lookup_tcgplayer_product_id", return_value=12345),
            patch("pokequant.scraper._fetch_tcgplayer_history", return_value=tcg_supplement),
            patch("pokequant.scraper._cache_get", return_value=None),
            patch("pokequant.scraper._cache_put"),
        ):
            return fetch_sales(card_name="Charizard V", days=days, use_cache=False, grade=grade)

    def test_supplement_fires_for_raw(self):
        """With <15 PC results and days=90 and grade=raw, TCGPlayer records are added."""
        sales = self._run_fetch(grade="raw", pc_sales_count=5, days=90)
        sources = {s["source"] for s in sales}
        assert "tcgplayer" in sources, "TCGPlayer supplement should fire for raw grade"
        assert len(sales) == 8  # 5 PC + 3 TCGPlayer

    def test_supplement_blocked_for_psa9(self):
        """PSA 9 queries must NOT get the TCGPlayer supplement."""
        sales = self._run_fetch(grade="psa9", pc_sales_count=5, days=90)
        sources = {s["source"] for s in sales}
        assert "tcgplayer" not in sources, "TCGPlayer supplement must not fire for psa9"
        assert len(sales) == 5

    def test_supplement_blocked_for_psa10(self):
        """PSA 10 queries must NOT get the TCGPlayer supplement."""
        sales = self._run_fetch(grade="psa10", pc_sales_count=5, days=90)
        sources = {s["source"] for s in sales}
        assert "tcgplayer" not in sources, "TCGPlayer supplement must not fire for psa10"
        assert len(sales) == 5

    def test_supplement_not_fired_when_enough_sales(self):
        """Does not fire when PC already returned >= 15 records."""
        sales = self._run_fetch(grade="raw", pc_sales_count=15, days=90)
        sources = {s["source"] for s in sales}
        assert "tcgplayer" not in sources
        assert len(sales) == 15

    def test_supplement_not_fired_for_short_window(self):
        """Does not fire when days < 90 (short windows don't need supplement)."""
        sales = self._run_fetch(grade="raw", pc_sales_count=5, days=30)
        sources = {s["source"] for s in sales}
        assert "tcgplayer" not in sources

    def test_supplement_deduplicates_by_date(self):
        """TCGPlayer records whose dates already exist in PC sales are dropped."""
        from pokequant.scraper import fetch_sales

        today = date.today()
        overlap_date = (today - timedelta(days=5)).isoformat()

        pc_sales = [
            {"sale_id": "pc_001", "price": 20.0, "date": overlap_date,
             "condition": "NM", "source": "pricecharting", "quantity": 1},
        ]
        # TCGPlayer returns same date — should be deduplicated away.
        tcg_sales = [
            {"sale_id": "tcg_001", "price": 18.0, "date": overlap_date,
             "condition": "NM", "source": "tcgplayer", "quantity": 1},
            {"sale_id": "tcg_002", "price": 19.0,
             "date": (today - timedelta(days=100)).isoformat(),
             "condition": "NM", "source": "tcgplayer", "quantity": 1},
        ]

        with (
            patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales),
            patch("pokequant.scraper._scrape_ebay", return_value=[]),
            patch("pokequant.scraper._lookup_tcgplayer_product_id", return_value=12345),
            patch("pokequant.scraper._fetch_tcgplayer_history", return_value=tcg_sales),
            patch("pokequant.scraper._cache_get", return_value=None),
            patch("pokequant.scraper._cache_put"),
        ):
            result = fetch_sales(
                card_name="Charizard V", days=90, use_cache=False, grade="raw"
            )

        assert len(result) == 2  # pc_001 + tcg_002 (tcg_001 deduped by date)
        result_dates = [s["date"] for s in result]
        # Only one record should have the overlap date (the PC one).
        assert result_dates.count(overlap_date) == 1
