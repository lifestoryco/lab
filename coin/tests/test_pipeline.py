import sys, os, tempfile, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _fresh_db(monkeypatch_path: str):
    """Return a pipeline module configured with a temp DB."""
    os.environ["COIN_DB_PATH"] = monkeypatch_path
    import config
    importlib.reload(config)
    from careerops import pipeline
    importlib.reload(pipeline)
    pipeline.init_db()
    return pipeline


def test_upsert_and_get(tmp_path):
    db = tmp_path / "pipeline.db"
    p = _fresh_db(str(db))
    role_id = p.upsert_role({
        "url": "https://example.com/job/1",
        "title": "Staff TPM",
        "company": "Acme",
        "lane": "cox-style-tpm",
        "source": "test",
    })
    assert role_id > 0
    got = p.get_role(role_id)
    assert got["title"] == "Staff TPM"
    assert got["status"] == "discovered"


def test_fit_score_flips_status(tmp_path):
    db = tmp_path / "pipeline.db"
    p = _fresh_db(str(db))
    role_id = p.upsert_role({"url": "https://example.com/job/2", "title": "X", "lane": "cox-style-tpm"})
    p.update_fit_score(role_id, 78.0)
    got = p.get_role(role_id)
    assert got["fit_score"] == 78.0
    assert got["status"] == "scored"


def test_status_transition_with_note(tmp_path):
    db = tmp_path / "pipeline.db"
    p = _fresh_db(str(db))
    role_id = p.upsert_role({"url": "https://example.com/job/3", "title": "X", "lane": "cox-style-tpm"})
    p.update_status(role_id, "applied", note="submitted via portal")
    got = p.get_role(role_id)
    assert got["status"] == "applied"
    assert "submitted via portal" in (got["notes"] or "")


def test_invalid_status_rejected(tmp_path):
    db = tmp_path / "pipeline.db"
    p = _fresh_db(str(db))
    role_id = p.upsert_role({"url": "https://example.com/job/4", "title": "X", "lane": "cox-style-tpm"})
    try:
        p.update_status(role_id, "totally_bogus")
    except ValueError:
        return
    raise AssertionError("ValueError not raised for bogus status")


def test_summary_structure(tmp_path):
    db = tmp_path / "pipeline.db"
    p = _fresh_db(str(db))
    p.upsert_role({"url": "https://example.com/job/5", "title": "X", "lane": "cox-style-tpm", "comp_min": 200000})
    s = p.summary()
    assert "counts" in s and "total" in s and "active_comp_floor" in s
    assert s["total"] == 1
