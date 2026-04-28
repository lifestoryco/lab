"""Tests for careerops.boards.ashby — Ashby board scraper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from careerops.boards.ashby import AshbyBoard

FIXTURE = Path(__file__).parent / "fixtures" / "boards" / "ashby_vercel.json"


class _FakeResp:
    def __init__(self, payload, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def _patch_get(monkeypatch, payload, status=200, captured: dict | None = None):
    def fake_get(self, url, params=None):
        if captured is not None:
            captured["url"] = url
            captured["params"] = params
        if status >= 400:
            return None
        return _FakeResp(payload, status)
    monkeypatch.setattr(AshbyBoard, "_get", fake_get)


@pytest.fixture
def ashby_payload():
    return json.loads(FIXTURE.read_text())


def test_parses_basic_job(monkeypatch, ashby_payload):
    _patch_get(monkeypatch, ashby_payload)
    rows = AshbyBoard().fetch_listings("vercel", "lane")
    assert len(rows) == 3
    epm = rows[0]
    assert epm["title"] == "Engineering Program Manager"
    assert epm["url"].startswith("https://jobs.ashbyhq.com/vercel/abc-789")
    assert epm["source"] == "ashby"


def test_comp_from_compensationTier_explicit(monkeypatch, ashby_payload):
    _patch_get(monkeypatch, ashby_payload)
    rows = AshbyBoard().fetch_listings("vercel", "lane")
    epm = rows[0]
    assert epm["comp_min"] == 170000
    assert epm["comp_max"] == 220000
    assert epm["comp_source"] == "explicit"


def test_comp_from_compensationTierSummary_explicit(monkeypatch, ashby_payload):
    _patch_get(monkeypatch, ashby_payload)
    rows = AshbyBoard().fetch_listings("vercel", "lane")
    se = rows[1]  # tier dict empty, summary string only
    assert se["comp_min"] == 150000
    assert se["comp_max"] == 200000
    assert se["comp_source"] == "explicit"


def test_comp_from_descriptionPlain_parsed(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": "x",
                "title": "Some role",
                "jobUrl": "https://jobs.ashbyhq.com/foo/x",
                "location": "Remote",
                "isRemote": True,
                "publishedAt": "2026-04-01T00:00:00Z",
                "descriptionPlain": "Salary range: $130,000 - $160,000.",
                "compensation": {}
            }
        ]
    }
    _patch_get(monkeypatch, payload)
    rows = AshbyBoard().fetch_listings("foo", "lane")
    assert rows[0]["comp_min"] == 130000
    assert rows[0]["comp_max"] == 160000
    assert rows[0]["comp_source"] == "parsed"


def test_comp_missing(monkeypatch, ashby_payload):
    _patch_get(monkeypatch, ashby_payload)
    rows = AshbyBoard().fetch_listings("vercel", "lane")
    pmm = rows[2]
    assert pmm["comp_min"] is None
    assert pmm["comp_max"] is None
    assert pmm["comp_source"] == "parsed"


def test_location_remote_flagged(monkeypatch, ashby_payload):
    _patch_get(monkeypatch, ashby_payload)
    rows = AshbyBoard().fetch_listings("vercel", "lane")
    assert rows[0]["remote"] == 1  # "Remote (United States)"
    assert rows[1]["remote"] == 0  # "Salt Lake City, UT"


def test_includeCompensation_param_sent(monkeypatch, ashby_payload):
    captured: dict = {}
    _patch_get(monkeypatch, ashby_payload, captured=captured)
    AshbyBoard().fetch_listings("vercel", "lane")
    assert captured["params"] == {"includeCompensation": "true"}


def test_404_returns_empty_list(monkeypatch):
    _patch_get(monkeypatch, {}, status=404)
    rows = AshbyBoard().fetch_listings("nonexistent", "lane")
    assert rows == []
