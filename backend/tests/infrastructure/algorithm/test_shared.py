from decimal import Decimal

import pytest

from tarakdingdung.infrastructure.algorithm.shared.numeric import ceil_to_step, floor_to_step
from tarakdingdung.infrastructure.algorithm.shared.ordering import symbol_key
from tarakdingdung.infrastructure.algorithm.shared.weights import GROSS_SAFETY, budget
from tests.infrastructure.algorithm.conformance import BTC_IDX, BTC_TKO, ETH_IDX


@pytest.mark.parametrize("value,step,expected", [
    ("1.23456", "0.001", "1.234"),
    ("1.0", "0.001", "1.0"),
    ("0.0000001", "0.001", "0"),
    ("5", "0", "5"),
    ("5", "-1", "5"),
])
def test_floor_to_step(value, step, expected):
    assert floor_to_step(Decimal(value), Decimal(step)) == Decimal(expected)


@pytest.mark.parametrize("value,step,expected", [
    ("1.2341", "0.001", "1.235"),
    ("1.234", "0.001", "1.234"),
    ("5", "0", "5"),
])
def test_ceil_to_step(value, step, expected):
    assert ceil_to_step(Decimal(value), Decimal(step)) == Decimal(expected)


def test_symbol_key_orders_by_venue_then_pair():
    assert sorted([BTC_TKO, ETH_IDX, BTC_IDX], key=symbol_key) == [
        BTC_IDX, ETH_IDX, BTC_TKO]


def test_budget_leaves_room_for_float_error():
    assert budget(1.0) < 1.0
    assert 1.0 - budget(1.0) == pytest.approx(GROSS_SAFETY)
