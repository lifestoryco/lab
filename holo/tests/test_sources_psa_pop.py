"""PSA Pop Report adapter — parser, env-flag gating, health_check."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from pokequant.sources.adapters.psa_pop import PSAPopAdapter


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("HOLO_ADAPTER_PSA_POP", raising=False)


def test_parses_grade_counts_from_text():
    html = """
    <html><body>
      <table>
        <tr><td>PSA 10</td><td>1,250</td></tr>
        <tr><td>PSA 9</td><td>3,400</td></tr>
        <tr><td>PSA 8</td><td>450</td></tr>
      </table>
    </body></html>
    """
    pop = PSAPopAdapter._parse(html, "https://example/card")
    assert pop["pop10"] == 1250
    assert pop["pop9"] == 3400
    assert pop["pop8"] == 450
    assert pop["total"] == 5100


def test_parse_returns_empty_when_no_grades_found():
    pop = PSAPopAdapter._parse("<html><body>Nothing here</body></html>", "https://x")
    assert pop == {}


def test_adapter_name_and_priority():
    a = PSAPopAdapter()
    assert a.name == "psa_pop"
    assert a.priority == 5
    assert a.supports_grade("raw")
    assert a.supports_grade("psa10")


def test_env_flag_disables_adapter(monkeypatch):
    monkeypatch.setenv("HOLO_ADAPTER_PSA_POP", "0")
    assert PSAPopAdapter().is_configured() is False


def test_env_flag_enables_adapter(monkeypatch):
    monkeypatch.setenv("HOLO_ADAPTER_PSA_POP", "1")
    assert PSAPopAdapter().is_configured() is True


def test_fetch_returns_pop_record_when_data_available():
    a = PSAPopAdapter()
    with patch.object(a, "fetch_pop", return_value={
        "pop10": 100, "pop9": 200, "pop8": 10, "total": 310, "url": "x"
    }):
        records = a.fetch("Charizard V", days=30, grade="raw")
    assert len(records) == 1
    r = records[0]
    assert r.source_type == "pop_report"
    assert r.extra["pop10"] == 100
    assert r.extra["total"] == 310


def test_fetch_returns_empty_when_no_pop_data():
    a = PSAPopAdapter()
    with patch.object(a, "fetch_pop", return_value={}):
        assert a.fetch("Unknown Card", days=30, grade="raw") == []


def test_health_check_handles_exception():
    a = PSAPopAdapter()
    with patch("pokequant.sources.adapters.psa_pop._http_session") as mock_s:
        mock_s.side_effect = RuntimeError("network down")
        hc = a.health_check()
    assert hc["ok"] is False
    assert "network down" in hc["error"]
