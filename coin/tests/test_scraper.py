"""Tests for the LinkedIn scraper card-parsing path, focused on m005's
posted_at extraction. Other scraper paths are covered indirectly by
integration tests; this file pins the per-card semantics."""

import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops import scraper
from careerops.scraper import _parse_linkedin_cards


def _wrap(card_html: str) -> str:
    """Wrap a single card snippet in the minimum HTML the parser needs."""
    return f"<ul>{card_html}</ul>"


_MINIMAL_CARD_PREFIX = (
    '<a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/123/">link</a>'
    '<h3 class="base-search-card__title">Senior TPM</h3>'
    '<h4 class="base-search-card__subtitle">Acme</h4>'
    '<span class="job-search-card__location">Remote</span>'
)


def test_parse_linkedin_card_extracts_posted_at_from_datetime_attr():
    card = (
        f'<li>{_MINIMAL_CARD_PREFIX}'
        '<time class="job-search-card__listdate" datetime="2026-04-20">2 weeks ago</time>'
        "</li>"
    )
    rows = _parse_linkedin_cards(_wrap(card))
    assert len(rows) == 1
    assert rows[0]["posted_at"] == "2026-04-20"


def test_parse_linkedin_card_extracts_posted_at_from_relative_string(monkeypatch):
    class _FixedDate(_dt.date):
        @classmethod
        def today(cls):
            return _dt.date(2026, 4, 27)

    monkeypatch.setattr(scraper.datetime, "date", _FixedDate)

    card = (
        f'<li>{_MINIMAL_CARD_PREFIX}'
        '<time class="job-search-card__listdate">Posted 3 days ago</time>'
        "</li>"
    )
    rows = _parse_linkedin_cards(_wrap(card))
    assert len(rows) == 1
    assert rows[0]["posted_at"] == "2026-04-24"


def test_parse_linkedin_card_posted_at_none_when_no_time_element():
    card = f"<li>{_MINIMAL_CARD_PREFIX}</li>"
    rows = _parse_linkedin_cards(_wrap(card))
    assert len(rows) == 1
    assert rows[0]["posted_at"] is None


def test_parse_linkedin_card_posted_at_none_when_unparseable():
    card = (
        f'<li>{_MINIMAL_CARD_PREFIX}'
        '<time class="job-search-card__listdate">brand new!</time>'
        "</li>"
    )
    rows = _parse_linkedin_cards(_wrap(card))
    assert len(rows) == 1
    assert rows[0]["posted_at"] is None
