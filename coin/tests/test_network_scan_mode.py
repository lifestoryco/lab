"""Structural tests for modes/network-scan.md and the network-patterns reference."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODE = ROOT / "modes" / "network-scan.md"
REF = ROOT / ".claude" / "skills" / "coin" / "references" / "network-patterns.md"


@pytest.fixture(scope="module")
def mode_text() -> str:
    return MODE.read_text()


@pytest.fixture(scope="module")
def ref_text() -> str:
    return REF.read_text()


def test_files_exist():
    assert MODE.exists()
    assert REF.exists()


def test_steps_present(mode_text):
    for n in range(1, 8):
        assert f"## Step {n}" in mode_text


def test_refusals_documented(mode_text):
    for refusal in [
        "Auto-sending DMs",
        "Inventing a shared history",
        "Scraping with Sean's logged-in session cookies",
        "out_of_band",
        "fit_score < 55",
        "Auto-setting `outreach.sent_at`",
    ]:
        assert refusal in mode_text, f"refusal not documented: {refusal}"


def test_never_auto_send_appears_twice(mode_text):
    occurrences = (
        mode_text.count("auto-send")
        + mode_text.count("NOT send")
        + mode_text.count("Never auto")
        + mode_text.count("never auto")
        + mode_text.count("Never auto-set")
    )
    assert occurrences >= 2, f"'never auto-send' should appear ≥ 2 times, found {occurrences}"


def test_warmth_weights_documented(mode_text, ref_text):
    # mode points at the 40/35/25 weights
    combined = mode_text + ref_text
    assert "0.40*recency" in combined or "40%" in combined
    assert "0.35*seniority" in combined or "35%" in combined
    assert "0.25*relevance" in combined or "25%" in combined
    assert "recency_score" in combined
    assert "seniority_score" in combined
    assert "relevance_score" in combined


def test_recency_tiers_documented(ref_text):
    assert "≤ 12 months" in ref_text
    assert "12–36 months" in ref_text
    assert "> 36 months" in ref_text


def test_truthfulness_gate_referenced(mode_text):
    assert "_shared.md" in mode_text
    assert "Operating Principle" in mode_text


def test_schema_creates_required_tables(tmp_path):
    """Run import script's schema-creation against a temp DB."""
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.import_linkedin_connections import ensure_schema

    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    try:
        ensure_schema(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "connections" in tables
        assert "outreach" in tables
        # Required columns on connections
        cols = {r[1] for r in conn.execute("PRAGMA table_info(connections)").fetchall()}
        for required in [
            "id", "first_name", "last_name", "linkedin_url", "company",
            "company_normalized", "position", "connected_on", "seniority",
            "last_seen", "notes",
        ]:
            assert required in cols, f"connections missing column: {required}"
        # Required columns on outreach
        outreach_cols = {r[1] for r in conn.execute("PRAGMA table_info(outreach)").fetchall()}
        for required in [
            "id", "role_id", "connection_id", "drafted_at", "sent_at",
            "replied_at", "warmth_score", "draft_message",
        ]:
            assert required in outreach_cols, f"outreach missing column: {required}"
    finally:
        conn.close()
