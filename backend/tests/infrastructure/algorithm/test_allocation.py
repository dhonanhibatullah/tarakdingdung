import pytest

from tarakdingdung.domain.models.algorithm import Signals
from tarakdingdung.infrastructure.algorithm.allocation.conviction_weighted import (
    ConvictionWeightedAllocator,
)
from tarakdingdung.infrastructure.algorithm.allocation.equal_weight import EqualWeightAllocator
from tests.infrastructure.algorithm.conformance import (
    BTC_IDX, BTC_TKO, ETH_IDX, TS, portfolio,
)


def signals(scores) -> Signals:
    return Signals(timestamp=TS, scores=scores)


def test_equal_weight_splits_the_budget():
    weights = EqualWeightAllocator().allocate(
        signals({BTC_IDX: 1.0, ETH_IDX: 0.4}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)
    assert weights.weights[ETH_IDX] == pytest.approx(0.5)


def test_equal_weight_ignores_conviction_when_sizing():
    weights = EqualWeightAllocator().allocate(
        signals({BTC_IDX: 1.0, ETH_IDX: 0.01}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(weights.weights[ETH_IDX])


def test_equal_weight_respects_max_positions_by_conviction():
    weights = EqualWeightAllocator(max_positions=2).allocate(
        signals({BTC_IDX: 0.1, ETH_IDX: 0.9, BTC_TKO: 0.5}), portfolio())
    assert set(weights.weights) == {ETH_IDX, BTC_TKO}


def test_equal_weight_honours_a_partial_budget():
    weights = EqualWeightAllocator(max_gross=0.5).allocate(
        signals({BTC_IDX: 1.0}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)


def test_equal_weight_shorts_on_a_negative_signal():
    weights = EqualWeightAllocator().allocate(
        signals({BTC_IDX: -1.0, ETH_IDX: 1.0}), portfolio())
    assert weights.weights[BTC_IDX] < 0
    assert weights.weights[ETH_IDX] > 0


def test_zero_signals_are_not_positions():
    weights = EqualWeightAllocator().allocate(
        signals({BTC_IDX: 0.0, ETH_IDX: 1.0}), portfolio())
    assert set(weights.weights) == {ETH_IDX}
    assert weights.weights[ETH_IDX] == pytest.approx(1.0)


def test_conviction_weighting_is_proportional():
    weights = ConvictionWeightedAllocator().allocate(
        signals({BTC_IDX: 0.75, ETH_IDX: 0.25}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.75)
    assert weights.weights[ETH_IDX] == pytest.approx(0.25)


def test_conviction_weighting_preserves_sign():
    weights = ConvictionWeightedAllocator().allocate(
        signals({BTC_IDX: -0.5, ETH_IDX: 0.5}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(-0.5)


def test_conviction_weighting_honours_a_partial_budget():
    weights = ConvictionWeightedAllocator(max_gross=0.4).allocate(
        signals({BTC_IDX: 1.0}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.4)
