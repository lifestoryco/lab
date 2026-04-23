"""NormalizedSale schema + registry invariant enforcement."""
from __future__ import annotations

from datetime import date

import pytest

from pokequant.sources.exceptions import InvalidSaleRecord
from pokequant.sources.registry import _validate
from pokequant.sources.schema import NormalizedSale


def _base(**overrides) -> NormalizedSale:
    defaults = dict(
        sale_id="s1",
        adapter="pricecharting",
        source_type="sale",
        price=10.0,
        currency="USD",
        date=date(2026, 4, 20),
        condition="NM",
        grade="raw",
        source_url="https://pc/charizard",
    )
    defaults.update(overrides)
    return NormalizedSale(**defaults)


def test_valid_record_passes():
    _validate(_base())


def test_zero_price_rejected():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(price=0))


def test_negative_price_rejected():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(price=-5))


def test_absurd_price_rejected():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(price=2_000_000))


def test_unknown_currency_rejected():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(currency="XYZ"))  # type: ignore[arg-type]


def test_unknown_grade_rejected():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(grade="psa12"))  # type: ignore[arg-type]


def test_mixed_condition_forbidden_on_sale():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(source_type="sale", condition="mixed"))


def test_mixed_condition_only_on_market_estimate():
    # Allowed on market_estimate
    _validate(_base(source_type="market_estimate", condition="mixed"))
    # Forbidden on pop_report
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(source_type="pop_report", condition="mixed", price=1))


def test_lot_size_requires_sale_type():
    with pytest.raises(InvalidSaleRecord):
        _validate(_base(source_type="market_estimate", lot_size=3, condition="mixed"))


def test_to_dict_roundtrip():
    r = _base(extra={"note": "hi"})
    d = r.to_dict()
    assert d["adapter"] == "pricecharting"
    assert d["extra"] == {"note": "hi"}
    assert d["date"] == "2026-04-20"
