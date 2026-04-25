"""Unit tests for careerops.offer_math."""

from __future__ import annotations

import pytest

from careerops.offer_math import (
    delta_table,
    historical_hit_rate,
    state_tax_rate,
    three_year_tc,
    vest_curve,
    vest_share_y1,
    year_one_tc,
)


def _o(**overrides) -> dict:
    base = {
        "company": "Test Co",
        "title": "TPM",
        "base_salary": 200_000,
        "signing_bonus": 0,
        "annual_bonus_target_pct": 0.10,
        "annual_bonus_paid_history": None,
        "rsu_total_value": 100_000,
        "rsu_vesting_schedule": "25/25/25/25",
        "rsu_vest_years": 4,
        "rsu_cliff_months": 12,
        "remote_pct": 100,
        "state_tax": "UT",
    }
    base.update(overrides)
    return base


def test_vest_share_y1_even():
    assert vest_share_y1(_o(rsu_vesting_schedule="25/25/25/25")) == 0.25


def test_vest_share_y1_back_loaded():
    assert vest_share_y1(_o(rsu_vesting_schedule="5/15/40/40")) == 0.05


def test_vest_share_y1_long_cliff_zeros():
    assert vest_share_y1(_o(rsu_cliff_months=18)) == 0.0


def test_vest_share_y1_quarterly():
    assert vest_share_y1(_o(rsu_vesting_schedule="6.25/q")) == 0.25


def test_vest_share_y1_unknown_falls_back():
    # Empty schedule → default 0.25
    assert vest_share_y1(_o(rsu_vesting_schedule="")) == 0.25


def test_vest_curve_padding_and_cliff():
    curve = vest_curve(_o(rsu_vesting_schedule="100", rsu_vest_years=4, rsu_cliff_months=0))
    assert len(curve) == 4
    assert curve[0] == 1.0
    assert sum(curve) == pytest.approx(1.0)

    cliff_curve = vest_curve(_o(rsu_vesting_schedule="25/25/25/25", rsu_cliff_months=18))
    # Y1 zeroed, moved to Y2
    assert cliff_curve[0] == 0.0
    assert cliff_curve[1] == pytest.approx(0.50)


def test_historical_hit_rate_default():
    assert historical_hit_rate(_o(annual_bonus_paid_history=None)) == 1.0


def test_historical_hit_rate_average():
    rate = historical_hit_rate(_o(annual_bonus_paid_history='["100%","85%","120%"]'))
    assert rate == pytest.approx(1.0167, abs=0.001)


def test_historical_hit_rate_handles_garbage():
    assert historical_hit_rate(_o(annual_bonus_paid_history='not json')) == 1.0
    assert historical_hit_rate(_o(annual_bonus_paid_history='[]')) == 1.0


def test_state_tax_rate():
    assert state_tax_rate("UT") == 0.0465
    assert state_tax_rate("ut") == 0.0465  # case-insensitive
    assert state_tax_rate("WA") == 0.0
    assert state_tax_rate(None) == 0.0
    assert state_tax_rate("Oz") == 0.0  # unknown → default


def test_year_one_tc_components():
    o = _o(
        base_salary=185_000,
        signing_bonus=25_000,
        annual_bonus_target_pct=0.15,
        annual_bonus_paid_history='["100%","100%"]',
        rsu_total_value=120_000,
        rsu_vesting_schedule="25/25/25/25",
        state_tax="UT",
    )
    y1 = year_one_tc(o)
    assert y1["base"] == 185_000
    assert y1["signing"] == 25_000
    assert y1["rsu_y1"] == 30_000  # 120k * 0.25
    assert y1["bonus_y1"] == int(round(185_000 * 0.15 * 1.0))  # 27_750
    assert y1["total"] == 185_000 + 25_000 + 30_000 + 27_750
    # UT = 4.65%
    assert y1["effective_after_state_tax"] == int(round(y1["total"] * (1 - 0.0465)))


def test_three_year_tc_growth_ordering():
    o = _o(rsu_total_value=400_000, rsu_vesting_schedule="25/25/25/25")
    bear = three_year_tc(o, rsu_growth_pct=-20)
    neutral = three_year_tc(o, rsu_growth_pct=0)
    bull = three_year_tc(o, rsu_growth_pct=10)
    assert bear["total"] < neutral["total"] < bull["total"]


def test_three_year_tc_includes_all_components():
    y3 = three_year_tc(_o())
    for k in ("base_total", "signing", "rsu_total_3yr", "bonus_total", "total"):
        assert k in y3
    assert y3["total"] == (
        y3["base_total"] + y3["signing"] + y3["rsu_total_3yr"] + y3["bonus_total"]
    )


def test_delta_table_marks_baseline():
    a = _o(company="A", base_salary=200_000)
    b = _o(company="B", base_salary=180_000)
    deltas = delta_table([a, b])
    assert len(deltas) == 2
    assert deltas[0]["baseline"] is True
    assert deltas[1]["baseline"] is False
    # B is lower → delta_y1_vs_baseline is negative
    assert deltas[1]["delta_y1_vs_baseline"] < 0


def test_delta_table_empty_input():
    assert delta_table([]) == []
