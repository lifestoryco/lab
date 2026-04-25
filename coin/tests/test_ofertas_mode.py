"""Structural tests for modes/ofertas.md and migration 002."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODE = ROOT / "modes" / "ofertas.md"


@pytest.fixture(scope="module")
def mode_text() -> str:
    return MODE.read_text()


def test_mode_file_exists():
    assert MODE.exists(), "modes/ofertas.md must exist"


def test_steps_present(mode_text):
    for n in range(1, 8):
        assert f"## Step {n}" in mode_text, f"Step {n} missing"


def test_refusals_documented(mode_text):
    refusals = [
        "Recommending a specific offer",
        "Auto-setting `status='offer-accepted'",
        "Inventing leverage points",
        "Presenting tax math as advice",
        "Drafting an aggressive counter without a real anchor",
    ]
    for r in refusals:
        assert r in mode_text, f"refusal not documented: {r}"


def test_never_recommend_appears(mode_text):
    assert "does NOT recommend" in mode_text or "Decision support, not advocacy" in mode_text


def test_human_gate_for_accept_decline(mode_text):
    assert "human gate" in mode_text.lower()
    assert "Sean confirms" in mode_text


def test_truthfulness_gate_referenced(mode_text):
    assert "_shared.md" in mode_text
    assert "PROFILE" in mode_text


def test_growth_sensitivity_documented(mode_text):
    # The -20% / 0% / +10% bracketing scenarios must appear
    assert "-20%" in mode_text
    assert "+10%" in mode_text


def test_tax_disclaimer(mode_text):
    assert "approximation" in mode_text.lower()
    assert "CPA" in mode_text


def test_migration_creates_offers_table(tmp_path):
    """Run migration 002 against a temp DB; assert columns exist."""
    # Import via file path since 002_ is not a valid module name
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_002_offers_table", ROOT / "scripts" / "migrations" / "002_offers_table.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    db = tmp_path / "test.db"
    module.apply(db)

    conn = sqlite3.connect(str(db))
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(offers)").fetchall()}
        for required in [
            "id", "role_id", "company", "title", "received_at", "expires_at",
            "base_salary", "signing_bonus", "annual_bonus_target_pct",
            "annual_bonus_paid_history", "rsu_total_value",
            "rsu_vesting_schedule", "rsu_vest_years", "rsu_cliff_months",
            "remote_pct", "state_tax", "growth_signal", "status",
        ]:
            assert required in cols, f"missing column: {required}"
        # Idempotency
        module.apply(db)
        applied = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE id = ?",
            ("002_offers_table",),
        ).fetchone()[0]
        assert applied == 1
    finally:
        conn.close()
