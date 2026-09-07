from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import Side
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.infrastructure.algorithm.allocation import EqualWeightAllocator
from tarakdingdung.infrastructure.algorithm.feature import RollingWindowFeatureExtractor
from tarakdingdung.infrastructure.algorithm.metric import StandardPerformanceEvaluator
from tarakdingdung.infrastructure.algorithm.signal import (
    CrossSectionalMomentumSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.strategy import (
    BuyAndHoldStrategy, PipelineStrategy,
)
from tarakdingdung.infrastructure.algorithm.universe import StaticUniverseSelector
from tests.infrastructure.algorithm.conformance import BTC_IDX, ETH_IDX, BTC_TKO, TS, portfolio
from tests.infrastructure.algorithm.test_blocks import candles, snapshot


def _pipeline(universe) -> PipelineStrategy:
    return PipelineStrategy(
        universe=StaticUniverseSelector(universe),
        features=RollingWindowFeatureExtractor(momentum_window=3, fast_window=2,
                                               slow_window=3, volatility_window=3),
        signals=CrossSectionalMomentumSignalGenerator(long_only=True),
        allocator=EqualWeightAllocator())


RISING = candles([100.0, 101.0, 102.0, 103.0, 120.0])
FALLING = candles([100.0, 99.0, 98.0, 97.0, 80.0])
PRICES = {BTC_IDX: Decimal("120"), ETH_IDX: Decimal("80"), BTC_TKO: Decimal("50")}


def test_pipeline_allocates_to_the_stronger_symbol():
    strategy = _pipeline((BTC_IDX, ETH_IDX))
    weights = strategy.decide(
        snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES),
        portfolio())
    assert weights.weights.get(BTC_IDX, 0.0) > 0
    assert weights.weights.get(ETH_IDX, 0.0) == 0.0


def test_pipeline_respects_its_universe():
    # A symbol outside the universe must not even influence the ranking.
    strategy = _pipeline((BTC_IDX,))
    weights = strategy.decide(
        snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES),
        portfolio())
    assert set(weights.weights) <= {BTC_IDX}


def test_pipeline_is_all_cash_when_nothing_qualifies():
    strategy = _pipeline((BTC_IDX, ETH_IDX))
    weights = strategy.decide(snapshot(prices=PRICES), portfolio())
    assert weights.weights == {}


def test_pipeline_is_deterministic():
    strategy = _pipeline((BTC_IDX, ETH_IDX))
    snap = snapshot(candle_map={BTC_IDX: RISING, ETH_IDX: FALLING}, prices=PRICES)
    first = strategy.decide(snap, portfolio())
    second = strategy.decide(snap, portfolio())
    assert first.weights == second.weights


def test_pipeline_stamps_the_snapshot_timestamp():
    strategy = _pipeline((BTC_IDX,))
    weights = strategy.decide(
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


# --- metric -----------------------------------------------------------------

def curve(values) -> tuple[EquityPoint, ...]:
    return tuple(EquityPoint(timestamp=TS + i, equity=Decimal(str(v)))
                 for i, v in enumerate(values))


def fill(quantity: str, price: str, fee: str) -> Fill:
    return Fill(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal(quantity),
                price=Decimal(price), fee=Decimal(fee), timestamp=TS)


def test_evaluator_reports_net_and_the_cost_drag():
    report = StandardPerformanceEvaluator().evaluate(
        curve([1000, 1100]), (fill("1", "100", "50"),))
    assert report.net_return == pytest.approx(0.10)
    # Gross adds the fees back: what it would have earned trading for free.
    assert report.gross_return == pytest.approx(0.15)
    assert report.cost_drag == pytest.approx(0.05)
    assert report.trade_count == 1


def test_evaluator_measures_drawdown_from_the_peak():
    report = StandardPerformanceEvaluator().evaluate(curve([100, 150, 75, 120]), ())
    assert report.max_drawdown == pytest.approx(0.5)


def test_evaluator_returns_zero_sharpe_for_a_flat_curve():
    # No dispersion must not become an infinity that reads as spectacular.
    report = StandardPerformanceEvaluator().evaluate(curve([100, 100, 100]), ())
    assert report.sharpe == 0.0
    assert report.sortino == 0.0


def test_evaluator_sortino_ignores_upside_dispersion():
    rising = StandardPerformanceEvaluator().evaluate(curve([100, 110, 121, 133]), ())
    assert rising.sortino == 0.0
    assert rising.sharpe > 0


def test_evaluator_handles_a_degenerate_curve():
    empty = StandardPerformanceEvaluator().evaluate((), ())
    single = StandardPerformanceEvaluator().evaluate(curve([100]), ())
    zero_start = StandardPerformanceEvaluator().evaluate(curve([0, 100]), ())
    for report in (empty, single, zero_start):
        assert report.total_return == 0.0
        assert report.trade_count == 0


def test_evaluator_turnover_is_notional_over_starting_equity():
    report = StandardPerformanceEvaluator().evaluate(
        curve([1000, 1000]), (fill("2", "100", "0"), fill("3", "100", "0")))
    assert report.turnover == pytest.approx(0.5)


def test_periods_per_year_scales_sharpe():
    daily = StandardPerformanceEvaluator(periods_per_year=365.0)
    hourly = StandardPerformanceEvaluator(periods_per_year=8760.0)
    points = curve([100, 101, 100.5, 102, 101.5, 103])
    assert hourly.evaluate(points, ()).sharpe > daily.evaluate(points, ()).sharpe
