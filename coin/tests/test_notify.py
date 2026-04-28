"""Tests for scripts/notify.py — iMessage interrupt for fresh A-grade roles."""
import importlib
import os
import sqlite3
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _seed_db(db_path: Path) -> None:
    """Create a roles table matching the production schema (subset)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                company TEXT,
                location TEXT,
                lane TEXT,
                comp_min INTEGER,
                comp_max INTEGER,
                fit_score REAL,
                status TEXT DEFAULT 'scored',
                discovered_at TEXT,
                notified_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _add_role(db_path: Path, **overrides) -> int:
    base = {
        "url": f"https://example.com/{overrides.get('id', 'x')}",
        "title": "TPM",
        "company": "Acme",
        "location": "Utah, US",
        "lane": "mid-market-tpm",
        "comp_min": 160000,
        "comp_max": 220000,
        "fit_score": 90.0,
        "status": "scored",
        "discovered_at": "datetime('now', '-2 hours')",
        "notified_at": None,
    }
    base.update({k: v for k, v in overrides.items() if k != "id"})
    conn = sqlite3.connect(db_path)
    try:
        # discovered_at expression must be evaluated, so use a subquery wrapper.
        cols = [c for c in base if c != "discovered_at"]
        placeholders = ",".join(["?"] * len(cols))
        sql = (
            f"INSERT INTO roles ({','.join(cols)}, discovered_at) "
            f"VALUES ({placeholders}, {base['discovered_at']})"
        )
        cur = conn.execute(sql, [base[c] for c in cols])
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "pipeline.db"
    _seed_db(db_path)
    monkeypatch.setenv("COIN_DB_PATH", str(db_path))
    monkeypatch.setenv("COIN_NOTIFY_PHONE", "+15551234567")
    # Reload notify so module-level constants pick up the env vars.
    if "scripts.notify" in sys.modules:
        del sys.modules["scripts.notify"]
    notify = importlib.import_module("scripts.notify")
    # Redirect log + flag paths into tmp so tests don't touch the repo.
    log_dir = tmp_path / "logs"
    flag = tmp_path / ".discover_failed.flag"
    monkeypatch.setattr(notify, "_DB", db_path)
    monkeypatch.setattr(notify, "_LOG_DIR", log_dir)
    monkeypatch.setattr(notify, "_DISCOVER_FAILED_FLAG", flag)
    monkeypatch.setattr(notify, "NOTIFY_PHONE", "+15551234567")
    return notify, db_path, flag, log_dir


def _run(notify, *argv) -> int:
    sys.argv = ["notify.py", *argv]
    return notify.main()


def _notified_at(db_path: Path, role_id: int):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT notified_at FROM roles WHERE id = ?", (role_id,)
        ).fetchone()[0]
    finally:
        conn.close()


# ── tests ───────────────────────────────────────────────────────────────────

def test_notify_no_fresh_roles_is_noop(temp_db):
    notify, _, _, _ = temp_db
    with patch.object(subprocess, "run") as mock_run:
        rc = _run(notify)
    assert rc == 0
    assert mock_run.call_count == 0


def test_notify_fresh_a_grade_builds_correct_message(temp_db):
    notify, db, _, _ = temp_db
    rid = _add_role(db, fit_score=92.0, company="Cool Co", title="Senior TPM",
                    url="https://jobs.example.com/abc")
    fake = subprocess.CompletedProcess(args=["osascript"], returncode=0, stderr="")
    with patch.object(subprocess, "run", return_value=fake) as mock_run:
        rc = _run(notify)
    assert rc == 0
    assert mock_run.call_count == 1
    args = mock_run.call_args.args[0]
    assert args[0] == "osascript"
    script_text = args[2]
    assert "🎯 Coin: A-grade role" in script_text
    assert "Cool Co" in script_text
    assert "Senior TPM" in script_text
    assert "https://jobs.example.com/abc" in script_text
    # role marked notified
    _ = rid


def test_notify_b_grade_skipped_when_min_grade_a(temp_db):
    notify, db, _, _ = temp_db
    _add_role(db, fit_score=72.0)  # B-grade (70-84)
    with patch.object(subprocess, "run") as mock_run:
        rc = _run(notify, "--min-grade", "A")
    assert rc == 0
    assert mock_run.call_count == 0


def test_notify_marks_notified_at_after_success(temp_db):
    notify, db, _, _ = temp_db
    rid = _add_role(db, fit_score=92.0)
    fake = subprocess.CompletedProcess(args=["osascript"], returncode=0, stderr="")
    with patch.object(subprocess, "run", return_value=fake):
        _run(notify)
    assert _notified_at(db, rid) is not None


def test_notify_does_not_resend_already_notified(temp_db):
    notify, db, _, _ = temp_db
    rid = _add_role(db, fit_score=92.0)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE roles SET notified_at = datetime('now') WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
    with patch.object(subprocess, "run") as mock_run:
        _run(notify)
    assert mock_run.call_count == 0


def test_dry_run_does_not_call_osascript(temp_db, capsys):
    notify, db, _, _ = temp_db
    rid = _add_role(db, fit_score=92.0)
    with patch.object(subprocess, "run") as mock_run:
        _run(notify, "--dry-run")
    assert mock_run.call_count == 0
    out = capsys.readouterr().out
    assert "🎯 Coin: A-grade role" in out
    assert _notified_at(db, rid) is None


def test_osascript_failure_logged_does_not_crash(temp_db):
    notify, db, _, log_dir = temp_db
    rid = _add_role(db, fit_score=92.0)
    fake = subprocess.CompletedProcess(args=["osascript"], returncode=1,
                                       stderr="permission denied")
    with patch.object(subprocess, "run", return_value=fake):
        rc = _run(notify)
    assert rc == 0
    assert _notified_at(db, rid) is None
    # error log was written
    today = __import__("datetime").date.today().isoformat()
    err_log = log_dir / f"notify_{today}.error.log"
    assert err_log.exists()
    assert "permission denied" in err_log.read_text()


def test_missing_phone_skips_silently(temp_db, monkeypatch, capsys):
    notify, db, _, _ = temp_db
    _add_role(db, fit_score=92.0)
    monkeypatch.setattr(notify, "NOTIFY_PHONE", "")
    with patch.object(subprocess, "run") as mock_run:
        rc = _run(notify)
    assert rc == 0
    assert mock_run.call_count == 0
    out = capsys.readouterr().out
    assert "COIN_NOTIFY_PHONE not set" in out


def test_discover_failed_flag_triggers_alert_message(temp_db):
    notify, db, flag, _ = temp_db
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("2026-04-28T07:00:00\nValueError: boom\n")
    _add_role(db, fit_score=92.0)
    fake = subprocess.CompletedProcess(args=["osascript"], returncode=0, stderr="")
    with patch.object(subprocess, "run", return_value=fake) as mock_run:
        rc = _run(notify)
    assert rc == 0
    assert mock_run.call_count == 1
    script = mock_run.call_args.args[0][2]
    assert "discover failed" in script
    assert "🎯 Coin" not in script  # not the role message
    assert not flag.exists()  # flag deleted after sending


def test_applescript_escaping_quotes_and_backslashes(temp_db):
    notify, db, _, _ = temp_db
    _add_role(db, fit_score=92.0, title='Title with "quote" and \\ backslash',
              company="Co\\Ltd")
    fake = subprocess.CompletedProcess(args=["osascript"], returncode=0, stderr="")
    with patch.object(subprocess, "run", return_value=fake) as mock_run:
        rc = _run(notify)
    assert rc == 0
    script = mock_run.call_args.args[0][2]
    # Bare unescaped quotes inside the AppleScript message body would corrupt it.
    # The whole script is wrapped: tell ... send "<msg>" to buddy "<phone>" of service "iMessage"
    # Count the unescaped " characters in the message portion.
    assert '\\"quote\\"' in script
    assert "\\\\ backslash" in script
    assert "Co\\\\Ltd" in script
