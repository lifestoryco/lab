"""Experience DB (m005) — schema, seed, query API, idempotency."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops import experience as exp
from scripts.migrations import m005_experience_db as m005
from scripts.migrations import m006_seed_lightcast as m006


# ── m005 schema ─────────────────────────────────────────────────────────

def test_m005_creates_all_tables(tmp_path):
    db = tmp_path / "t.db"
    m005.apply(db)
    conn = sqlite3.connect(str(db))
    try:
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for t in (
            "accomplishment", "outcome", "evidence", "skill",
            "accomplishment_skill", "lane", "accomplishment_lane",
            "bullet_variant", "jd_keyword", "render_artifact",
        ):
            assert t in tables, f"missing table {t}"
    finally:
        conn.close()


def test_m005_is_idempotent(tmp_path):
    db = tmp_path / "t.db"
    m005.apply(db)
    m005.apply(db)
    conn = sqlite3.connect(str(db))
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE id=?",
            ("005_experience_db",),
        ).fetchone()[0]
        assert n == 1
    finally:
        conn.close()


def test_m005_indexes_present(tmp_path):
    db = tmp_path / "t.db"
    m005.apply(db)
    conn = sqlite3.connect(str(db))
    try:
        idx = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        for required in (
            "idx_accomplishment_position",
            "idx_outcome_accomplishment",
            "idx_evidence_outcome",
            "idx_evidence_source",
            "idx_skill_category",
            "idx_render_artifact_role",
        ):
            assert required in idx
    finally:
        conn.close()


# ── m006 lightcast seed ────────────────────────────────────────────────

def test_m006_loads_skills(tmp_path):
    db = tmp_path / "t.db"
    n = m006.apply(db)
    assert n >= 500, f"expected ≥500 skills, got {n}"
    conn = sqlite3.connect(str(db))
    try:
        n_db = conn.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        assert n_db == n
        # Spot-check categories.
        cats = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT category FROM skill"
            ).fetchall()
        }
        for required in ("Wireless", "IoT", "Program Management", "Cloud", "Sales"):
            assert required in cats
    finally:
        conn.close()


def test_m006_bootstraps_m005_on_fresh_db(tmp_path):
    """Calling m006 on a fresh DB should auto-run m005 first."""
    db = tmp_path / "t.db"
    m006.apply(db)  # m005 not called explicitly
    conn = sqlite3.connect(str(db))
    try:
        applied = {
            r[0] for r in conn.execute(
                "SELECT id FROM schema_migrations"
            ).fetchall()
        }
        assert "005_experience_db" in applied
        assert "006_seed_lightcast" in applied
    finally:
        conn.close()


def test_m006_is_idempotent(tmp_path):
    db = tmp_path / "t.db"
    m006.apply(db)
    second = m006.apply(db)
    assert second == 0  # already-applied returns 0


# ── seed_from_base_py ──────────────────────────────────────────────────

def test_seed_from_base_py_creates_accomplishments(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    stats = seed(db)
    assert stats["lanes"] == 4
    assert stats["accomplishments_inserted"] >= 8
    assert stats["outcomes_inserted"] >= 5
    # Every outcome must have evidence (per locked decision #5).
    conn = sqlite3.connect(str(db))
    try:
        n_outcomes = conn.execute("SELECT COUNT(*) FROM outcome").fetchone()[0]
        n_evidence = conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE source='self_reported'"
        ).fetchone()[0]
        assert n_evidence == n_outcomes, "every outcome should have a self_reported evidence row"
    finally:
        conn.close()


def test_seed_from_base_py_is_idempotent(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    stats1 = seed(db)
    stats2 = seed(db)
    assert stats2["accomplishments_inserted"] == 0
    assert stats2["outcomes_inserted"] == 0
    assert stats2["evidence_inserted"] == 0


def test_seed_assigns_lane_relevance_to_proof_points(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    conn = sqlite3.connect(str(db))
    try:
        # cox_true_local_labs should map → mid-market-tpm at 100.
        rows = conn.execute("""
            SELECT a.id, l.slug, al.relevance_score
            FROM accomplishment_lane al
            JOIN accomplishment a ON a.id = al.accomplishment_id
            JOIN lane l ON l.id = al.lane_id
            WHERE l.slug = 'mid-market-tpm' AND al.relevance_score = 100
        """).fetchall()
        assert len(rows) >= 2  # cox + global_engineering_orchestration + safeguard
    finally:
        conn.close()


# ── experience.py read API ──────────────────────────────────────────────

def test_assemble_for_lane_returns_payload(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    payload = exp.assemble_for_lane("mid-market-tpm", min_relevance=60, db_path=db)
    assert len(payload) >= 2
    for entry in payload:
        assert "accomplishment" in entry
        assert "outcomes" in entry
        assert "evidence" in entry
        assert "skills" in entry
        assert "lane_relevance" in entry


def test_upsert_bullet_variant_idempotent(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    v1 = exp.upsert_bullet_variant(
        accomplishment_id=1, lane_slug="mid-market-tpm",
        length_bucket="short", text="Hello.", tone="commercial", db_path=db,
    )
    v2 = exp.upsert_bullet_variant(
        accomplishment_id=1, lane_slug="mid-market-tpm",
        length_bucket="short", text="Updated.", tone="commercial", db_path=db,
    )
    assert v1 == v2
    variants = exp.get_bullet_variants(accomplishment_id=1, db_path=db)
    assert variants[0]["text"] == "Updated."


def test_upsert_bullet_variant_rejects_invalid_length(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    with pytest.raises(ValueError):
        exp.upsert_bullet_variant(
            accomplishment_id=1, lane_slug="mid-market-tpm",
            length_bucket="huge", text="x", db_path=db,
        )


def test_insert_evidence_rejects_invalid_source(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    with pytest.raises(ValueError):
        exp.insert_evidence(
            outcome_id=1, kind="url", source="not_a_real_source",
            db_path=db,
        )


def test_upgrade_evidence_promotes_source(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    ev = exp.list_evidence(accomplishment_id=5, db_path=db)
    assert ev, "expected at least one evidence row on acc#5"
    exp.upgrade_evidence(
        ev[0]["id"], source="public", url_or_path="https://example.com",
        db_path=db,
    )
    after = exp.list_evidence(accomplishment_id=5, db_path=db)
    assert after[0]["source"] == "public"
    assert after[0]["url_or_path"] == "https://example.com"


def test_tag_skill_via_slug(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    ok = exp.tag_skill(
        accomplishment_id=5, skill_slug="technical-program-management",
        weight=9, db_path=db,
    )
    assert ok
    skills = exp.list_skills_for_accomplishment(5, db_path=db)
    assert any(s["slug"] == "technical-program-management" for s in skills)


def test_tag_skill_unknown_slug_returns_false(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    ok = exp.tag_skill(
        accomplishment_id=5, skill_slug="not-a-real-skill",
        weight=5, db_path=db,
    )
    assert ok is False


def test_render_artifact_round_trip(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    art_id = exp.insert_render_artifact(
        role_id=1, theme="harvard", variant_kind="designed",
        pdf_path="/tmp/test.pdf",
        ats_score=92, keyword_overlap_pct=72.0,
        buzzword_density_pct=2.1, truthfulness_pass=True,
        page_count=1, db_path=db,
    )
    assert art_id > 0
    rows = exp.list_render_artifacts(1, db_path=db)
    assert len(rows) == 1
    assert rows[0]["theme"] == "harvard"
    assert rows[0]["truthfulness_pass"] == 1


def test_render_artifact_rejects_invalid_variant(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    with pytest.raises(ValueError):
        exp.insert_render_artifact(
            role_id=1, theme="x", variant_kind="bogus",
            pdf_path="/tmp/x.pdf", db_path=db,
        )


def test_jd_keyword_upsert_dedupes_by_term(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    a = exp.upsert_jd_keyword(
        role_id=1, term="RF Engineering", term_kind="must_have",
        importance=8, db_path=db,
    )
    b = exp.upsert_jd_keyword(
        role_id=1, term="RF Engineering", term_kind="must_have",
        importance=10, db_path=db,
    )
    assert a == b  # same row updated
