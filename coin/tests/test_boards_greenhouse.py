"""Tests for careerops.boards.greenhouse — Greenhouse board scraper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from careerops.boards.greenhouse import GreenhouseBoard

FIXTURE = Path(__file__).parent / "fixtures" / "boards" / "greenhouse_filevine.json"


class _FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def _patch_get(monkeypatch, payload, status=200):
    """Patch _get on the instance to skip the live HTTP call."""
    def fake_get(self, url, params=None):
        if status >= 400:
            return None
        return _FakeResp(payload, status)
    monkeypatch.setattr(GreenhouseBoard, "_get", fake_get)


@pytest.fixture
def filevine_payload():
    return json.loads(FIXTURE.read_text())


def test_parses_basic_listing(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    board = GreenhouseBoard()
    rows = board.fetch_listings("filevine", "enterprise-sales-engineer")
    assert len(rows) == 3
    first = rows[0]
    assert first["title"] == "Senior Solutions Engineer"
    assert first["url"] == "https://boards.greenhouse.io/filevine/jobs/4567890"
    assert first["location"] == "Lehi, UT"
    assert first["source"] == "greenhouse"


def test_comp_from_metadata_explicit(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    rows = GreenhouseBoard().fetch_listings("filevine", "lane")
    se = rows[0]
    assert se["comp_min"] == 135000
    assert se["comp_max"] == 175000
    assert se["comp_source"] == "explicit"


def test_comp_from_content_html_parsed(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    rows = GreenhouseBoard().fetch_listings("filevine", "lane")
    tpm = rows[1]  # second job: only content has comp
    assert tpm["comp_min"] == 150000
    assert tpm["comp_max"] == 200000
    assert tpm["comp_source"] == "parsed"


def test_comp_missing_returns_none(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    rows = GreenhouseBoard().fetch_listings("filevine", "lane")
    ae = rows[2]
    assert ae["comp_min"] is None
    assert ae["comp_max"] is None
    assert ae["comp_source"] == "parsed"


def test_location_remote_flagged(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    rows = GreenhouseBoard().fetch_listings("filevine", "lane")
    assert rows[0]["remote"] == 0
    assert rows[1]["remote"] == 1  # "Remote — US"


def test_posted_at_iso_extracted(monkeypatch, filevine_payload):
    _patch_get(monkeypatch, filevine_payload)
    rows = GreenhouseBoard().fetch_listings("filevine", "lane")
    assert rows[0]["posted_at"].startswith("2026-04-22")


def test_404_returns_empty_list(monkeypatch):
    _patch_get(monkeypatch, {}, status=404)
    rows = GreenhouseBoard().fetch_listings("nonexistent-slug", "lane")
    assert rows == []


def test_empty_jobs_array(monkeypatch):
    _patch_get(monkeypatch, {"jobs": []})
    rows = GreenhouseBoard().fetch_listings("emptyboard", "lane")
    assert rows == []
