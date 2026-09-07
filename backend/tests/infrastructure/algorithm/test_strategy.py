from decimal import Decimal

import pytest

from tarakdingdung.infrastructure.algorithm.allocation.equal_weight import EqualWeightAllocator
from tarakdingdung.infrastructure.algorithm.feature.rolling_window import (
    RollingWindowFeatureExtractor,
)
from tarakdingdung.infrastructure.algorithm.signal.cross_sectional_momentum import (
    CrossSectionalMomentumSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.strategy.buy_and_hold import BuyAndHoldStrategy
from tarakdingdung.infrastructure.algorithm.strategy.pipeline import PipelineStrategy
from tarakdingdung.infrastructure.algorithm.universe.static import StaticUniverseSelector
from tests.infrastructure.algorithm.conformance import BTC_IDX, BTC_TKO, ETH_IDX, TS, portfolio
from tests.infrastructure.algorithm.fixtures import candles, snapshot

RISING = candles([100.0, 101.0, 102.0, 103.0, 120.0])
FALLING = candles([100.0, 99.0, 98.0, 97.0, 80.0])
PRICES = {BTC_IDX: Decimal("120"), ETH_IDX: Decimal("80"), BTC_TKO: Decimal("50")}


def pipeline(universe) -> PipelineStrategy:
    return PipelineStrategy(
        universe=StaticUniverseSelector(universe),
        features=RollingWindowFeatureExtractor(momentum_window=3, fast_window=2,
                                               slow_window=3, volatility_window=3),
        signals=CrossSectionalMomentumSignalGenerator(long_only=True),
        allocator=EqualWeightAllocator())


def test_allocates_to_the_stronger_symbol():
    weights = pipeline((BTC_IDX, ETH_IDX)).decide(
        snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES),
        portfolio())
    assert weights.weights.get(BTC_IDX, 0.0) > 0
    assert weights.weights.get(ETH_IDX, 0.0) == 0.0


def test_respects_its_universe():
    # A symbol outside the universe must not even influence the ranking.
    weights = pipeline((BTC_IDX,)).decide(
        snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES),
        portfolio())
    assert set(weights.weights) <= {BTC_IDX}


def test_is_all_cash_when_nothing_qualifies():
    weights = pipeline((BTC_IDX, ETH_IDX)).decide(snapshot(prices=PRICES), portfolio())
    assert weights.weights == {}


def test_is_deterministic():
    strategy = pipeline((BTC_IDX, ETH_IDX))
    snap = snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES)
    assert strategy.decide(snap, portfolio()).weights == strategy.decide(
        snap, portfolio()).weights


def test_stamps_the_snapshot_timestamp():
    weights = pipeline((BTC_IDX,)).decide(
        snapshot(candle_map={BTC_IDX: RISING}, prices=PRICES), portfolio())
    assert weights.timestamp == TS


def test_buy_and_hold_splits_across_available_symbols():
    weights = BuyAndHoldStrategy((BTC_IDX, ETH_IDX)).decide(
        snapshot(prices=PRICES), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)
    assert weights.weights[ETH_IDX] == pytest.approx(0.5)


def test_buy_and_hold_skips_symbols_the_snapshot_lacks():
    weights = BuyAndHoldStrategy((BTC_IDX, ETH_IDX)).decide(
        snapshot(prices={BTC_IDX: Decimal("120")}), portfolio())
    assert set(weights.weights) == {BTC_IDX}


def test_buy_and_hold_holds_nothing_when_nothing_is_tradable():
    assert BuyAndHoldStrategy((BTC_IDX,)).decide(
        snapshot(prices={}), portfolio()).weights == {}


def test_buy_and_hold_honours_a_partial_budget():
    weights = BuyAndHoldStrategy((BTC_IDX,), max_gross=0.5).decide(
        snapshot(prices=PRICES), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)
