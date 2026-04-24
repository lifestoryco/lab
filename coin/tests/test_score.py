import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops.score import score_comp, score_title, score_remote, score_fit


def test_comp_unverified_middle():
    assert score_comp(None, None) == 55.0


def test_comp_above_total_floor():
    assert score_comp(260000, 320000) == 100.0


def test_comp_between_floors():
    s = score_comp(200000, 250000)
    assert 60 <= s <= 100


def test_comp_below_base_floor():
    s = score_comp(100000, 120000)
    assert 0 <= s < 60


def test_title_exclusion_zeroes_out():
    assert score_title("Junior Technical Program Manager", "cox-style-tpm") == 0.0


def test_title_hit():
    assert score_title("Staff Technical Program Manager", "cox-style-tpm") == 100.0


def test_remote_explicit():
    assert score_remote({"remote": 1}) == 100.0


def test_remote_hybrid_location():
    assert score_remote({"remote": 0, "location": "Hybrid - New York"}) == 70.0


def test_full_fit_basic():
    role = {
        "title": "Staff Technical Program Manager",
        "company": "Acme",
        "location": "Remote, United States",
        "remote": 1,
        "comp_min": 220000,
        "comp_max": 290000,
    }
    fit = score_fit(role, "cox-style-tpm")
    # title perfect + remote perfect + comp decent + skills via lane keywords
    assert fit >= 70
