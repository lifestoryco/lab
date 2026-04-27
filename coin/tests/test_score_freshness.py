"""Tests for score_freshness — the m005 freshness dimension."""

import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops import score as score_mod
from careerops.score import score_freshness


def _freeze_today(monkeypatch, year: int, month: int, day: int) -> _dt.date:
    today = _dt.date(year, month, day)

    class _FixedDate(_dt.date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(score_mod.datetime, "date", _FixedDate)
    return today


def test_score_freshness_fresh(monkeypatch):
    today = _freeze_today(monkeypatch, 2026, 4, 27)
    posted = (today - _dt.timedelta(days=3)).isoformat()
    assert score_freshness(posted) == 100


def test_score_freshness_recent(monkeypatch):
    today = _freeze_today(monkeypatch, 2026, 4, 27)
    posted = (today - _dt.timedelta(days=10)).isoformat()
    assert score_freshness(posted) == 80


def test_score_freshness_aging(monkeypatch):
    today = _freeze_today(monkeypatch, 2026, 4, 27)
    posted = (today - _dt.timedelta(days=20)).isoformat()
    assert score_freshness(posted) == 60


def test_score_freshness_stale(monkeypatch):
    today = _freeze_today(monkeypatch, 2026, 4, 27)
    posted = (today - _dt.timedelta(days=60)).isoformat()
    assert score_freshness(posted) == 30


def test_score_freshness_ancient(monkeypatch):
    today = _freeze_today(monkeypatch, 2026, 4, 27)
    posted = (today - _dt.timedelta(days=200)).isoformat()
    assert score_freshness(posted) == 10


def test_score_freshness_unknown_returns_neutral():
    assert score_freshness(None) == 50


def test_score_freshness_unparseable_returns_neutral():
    assert score_freshness("not a date") == 50
