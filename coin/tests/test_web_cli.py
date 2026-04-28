"""Tests for careerops/web_cli.py — JSON CLI shim for web mutations."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import careerops.pipeline as pip_mod

_PYTHON = sys.executable
_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("COIN_DB_PATH", str(tmp_path / "pipeline.db"))
    monkeypatch.setattr(pip_mod, "DB_PATH", str(tmp_path / "pipeline.db"))
    pip_mod.init_db()
    return tmp_path


def _role_id(db_path) -> int:
    monkeypatch_db = str(db_path / "pipeline.db")
    import sqlite3
    conn = sqlite3.connect(monkeypatch_db)
    conn.execute("""
        INSERT INTO roles (url, title, company, lane, status, discovered_at, updated_at)
        VALUES ('https://ex.com/1', 'Senior TPM', 'Acme', 'mid-market-tpm',
                'discovered', datetime('now'), datetime('now'))
    """)
    conn.commit()
    rid = conn.execute("SELECT id FROM roles ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()
    return rid


def _run(*extra_args, env=None):
    cmd = [_PYTHON, "-m", "careerops.web_cli"] + list(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_ROOT), env=env)
    return result


# ── Test 1: track happy path ─────────────────────────────────────────────────


def test_track_happy_path(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("track", "--id", str(rid), "--status", "scored", env=env)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["status"] == "scored"
    assert data["previous_status"] == "discovered"
    assert data["role_id"] == rid


# ── Test 2: track with note ───────────────────────────────────────────────────


def test_track_with_note(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("track", "--id", str(rid), "--status", "scored", "--note", "moved by test", env=env)
    assert result.returncode == 0
    role = pip_mod.get_role(rid)
    assert "moved by test" in (role.get("notes") or "")


# ── Test 3: track bad role_id ─────────────────────────────────────────────────


def test_track_bad_role_id(db):
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("track", "--id", "99999", "--status", "scored", env=env)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["code"] == "ROLE_NOT_FOUND"


# ── Test 4: track invalid status ─────────────────────────────────────────────


def test_track_invalid_status(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("track", "--id", str(rid), "--status", "bogus_status", env=env)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["code"] == "INVALID_STATUS"


# ── Test 5: tailor happy path ─────────────────────────────────────────────────


def test_tailor_happy_path(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("tailor", "--id", str(rid), env=env)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["queued"] is True
    # Marker file should exist under coin/data/tailor_pending/
    marker = _ROOT / "data" / "tailor_pending" / f"{rid}.txt"
    assert marker.exists(), f"marker file not found at {marker}"
    marker.unlink()  # clean up real data dir
    # Notes updated
    role = pip_mod.get_role(rid)
    assert "tailor requested via web" in (role.get("notes") or "")


# ── Test 6: tailor bad role_id ────────────────────────────────────────────────


def test_tailor_bad_role_id(db):
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("tailor", "--id", "99999", env=env)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["code"] == "ROLE_NOT_FOUND"


# ── Test 7: notes append ──────────────────────────────────────────────────────


def test_notes_append(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("notes", "--id", str(rid), "--append", "interesting company", env=env)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["appended"] == len("interesting company")
    role = pip_mod.get_role(rid)
    assert "interesting company" in (role.get("notes") or "")


# ── Test 8: notes empty text is a user error ─────────────────────────────────


def test_notes_empty_text(db):
    rid = _role_id(db)
    env = {**os.environ, "COIN_DB_PATH": str(db / "pipeline.db")}
    result = _run("notes", "--id", str(rid), "--append", "", env=env)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["code"] == "EMPTY_TEXT"
