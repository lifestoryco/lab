"""CORS origin allowlist — api/index.py::_resolve_allowed_origin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.index import _resolve_allowed_origin  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_vercel_env(monkeypatch):
    monkeypatch.delenv("VERCEL_ENV", raising=False)


def test_prod_www_origin_allowed():
    assert _resolve_allowed_origin("https://www.handoffpack.com") == "https://www.handoffpack.com"


def test_prod_apex_origin_allowed():
    assert _resolve_allowed_origin("https://handoffpack.com") == "https://handoffpack.com"


def test_preview_vercel_origin_allowed():
    origin = "https://handoffpack-www-git-feat-foo-myteam.vercel.app"
    assert _resolve_allowed_origin(origin) == origin


def test_random_vercel_origin_denied():
    # .vercel.app alone is not enough — must contain handoffpack-www
    assert _resolve_allowed_origin("https://evil.vercel.app") is None


def test_evil_origin_denied():
    assert _resolve_allowed_origin("https://evil.com") is None


def test_empty_origin_returns_none():
    assert _resolve_allowed_origin("") is None


def test_localhost_allowed_outside_production(monkeypatch):
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert _resolve_allowed_origin("http://localhost:3000") == "http://localhost:3000"


def test_localhost_denied_in_production(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert _resolve_allowed_origin("http://localhost:3000") is None


def test_localhost_allowed_in_preview(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert _resolve_allowed_origin("http://localhost:3000") == "http://localhost:3000"


def test_spoofed_subdomain_denied():
    # "handoffpack.com.evil.com" must not match prod set
    assert _resolve_allowed_origin("https://handoffpack.com.evil.com") is None
