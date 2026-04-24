import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops.compensation import parse_comp_string, filter_by_comp, comp_band_label


def test_parse_explicit_range():
    mn, mx = parse_comp_string("$180K–$240K")
    assert mn == 180000
    assert mx == 240000


def test_parse_no_comp():
    mn, mx = parse_comp_string(None)
    assert mn is None and mx is None


def test_filter_keeps_unverified():
    roles = [{"comp_raw": None, "title": "TPM"}]
    result = filter_by_comp(roles, min_base=180000)
    assert len(result) == 1


def test_filter_removes_low_comp():
    roles = [{"comp_raw": "$80K–$100K", "title": "Coordinator"}]
    result = filter_by_comp(roles, min_base=180000)
    assert len(result) == 0


def test_filter_keeps_high_comp():
    roles = [{"comp_raw": "$200K–$280K", "title": "Senior TPM"}]
    result = filter_by_comp(roles, min_base=180000)
    assert len(result) == 1


def test_comp_band_label():
    assert comp_band_label(180000, 240000) == "$180K–$240K"
    assert comp_band_label(None, None) == "unverified"
