"""130point adapter — parser, outlier flagging, date windowing."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from pokequant.sources.adapters.onethreezero_point import OneThirtyPointAdapter


def _fixture_html(date_str: str, price: str = "125.00", extra: str = "") -> str:
    return f"""
    <html><body>
      <table>
        <tr><th>Date</th><th>Price</th><th>Title</th></tr>
        <tr>
          <td>{date_str}</td>
          <td>${price}</td>
          <td>Charizard VMAX 020/189 Darkness Ablaze Near Mint {extra}</td>
        </tr>
      </table>
    </body></html>
    """


def test_parses_single_sale_row():
    today = date.today().strftime("%Y-%m-%d")
    html = _fixture_html(today, "125.00")
    records = list(OneThirtyPointAdapter._parse(html, "Charizard VMAX 20", "https://130point", 30))
    assert len(records) == 1
    r = records[0]
    assert r.price == 125.0
    assert r.source_type == "sale"
    assert r.adapter == "130point"
    assert r.currency == "USD"
    assert r.confidence == 0.9


def test_outlier_flagged_on_lot_keyword():
    today = date.today().strftime("%Y-%m-%d")
    html = _fixture_html(today, "300.00", extra="(lot of 3)")
    records = list(OneThirtyPointAdapter._parse(html, "Charizard", "https://130point", 30))
    assert len(records) == 1
    assert records[0].outlier_flag is True


def test_row_outside_window_dropped():
    old = (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")
    html = _fixture_html(old, "100.00")
    records = list(OneThirtyPointAdapter._parse(html, "Charizard", "https://130point", 30))
    assert records == []


def test_slash_date_format_supported():
    today_us = date.today().strftime("%m/%d/%Y")
    html = _fixture_html(today_us, "75.00")
    records = list(OneThirtyPointAdapter._parse(html, "Pikachu", "https://130point", 30))
    assert len(records) == 1
    assert records[0].price == 75.0


def test_graded_grade_request_returns_empty():
    a = OneThirtyPointAdapter()
    assert a.fetch("Charizard", days=30, grade="psa10") == []


def test_adapter_priority_and_name():
    a = OneThirtyPointAdapter()
    assert a.name == "130point"
    assert a.priority == 85
    assert a.supports_grade("raw")
    assert not a.supports_grade("psa10")


def test_price_with_comma_thousands_separator():
    today = date.today().strftime("%Y-%m-%d")
    html = _fixture_html(today, "1,250.00")
    records = list(OneThirtyPointAdapter._parse(html, "Charizard", "https://130point", 30))
    assert len(records) == 1
    assert records[0].price == 1250.0


def test_malformed_row_skipped():
    html = "<html><body><table><tr><td>only one cell</td></tr></table></body></html>"
    records = list(OneThirtyPointAdapter._parse(html, "x", "https://130point", 30))
    assert records == []
