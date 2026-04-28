"""Tests for careerops.boards.lever — Lever board scraper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from careerops.boards.lever import LeverBoard

FIXTURE = Path(__file__).parent / "fixtures" / "boards" / "lever_lucidsoftware.json"


class _FakeResp:
    def __init__(self, payload, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def _patch_get(monkeypatch, payload, status=200):
    def fake_get(self, url, params=None):
        if status >= 400:
            return None
        return _FakeResp(payload, status)
    monkeypatch.setattr(LeverBoard, "_get", fake_get)


@pytest.fixture
def lever_payload():
    return json.loads(FIXTURE.read_text())


def test_parses_basic_posting(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    assert len(rows) == 3
    sa = rows[0]
    assert sa["title"] == "Staff Solutions Architect"
    assert sa["url"] == "https://jobs.lever.co/lucidsoftware/abc-123"
    assert sa["source"] == "lever"


def test_comp_from_salaryRange_explicit(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    sa = rows[0]
    assert sa["comp_min"] == 140000
    assert sa["comp_max"] == 190000
    assert sa["comp_source"] == "explicit"


def test_comp_from_descriptionPlain_parsed(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    tpm = rows[1]  # no salaryRange, only prose
    assert tpm["comp_min"] == 130000
    assert tpm["comp_max"] == 170000
    assert tpm["comp_source"] == "parsed"


def test_comp_missing(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    mkt = rows[2]
    assert mkt["comp_min"] is None
    assert mkt["comp_max"] is None
    assert mkt["comp_source"] == "parsed"


def test_location_remote_flagged(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    assert rows[0]["remote"] == 0  # "South Jordan, UT"
    assert rows[1]["remote"] == 1  # "Remote - United States" + workplaceType=remote


def test_hostedUrl_used_as_canonical(monkeypatch, lever_payload):
    _patch_get(monkeypatch, lever_payload)
    rows = LeverBoard().fetch_listings("lucidsoftware", "lane")
    for r in rows:
        # hostedUrl is the public-facing canonical link; not the apply URL
        assert "/apply" not in r["url"]


def test_404_returns_empty_list(monkeypatch):
    _patch_get(monkeypatch, [], status=404)
    rows = LeverBoard().fetch_listings("nonexistent", "lane")
    assert rows == []


def test_empty_array(monkeypatch):
    _patch_get(monkeypatch, [])
    rows = LeverBoard().fetch_listings("emptyboard", "lane")
    assert rows == []
