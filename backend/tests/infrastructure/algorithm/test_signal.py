import pytest

from tarakdingdung.domain.models.algorithm import FeatureSet
from tarakdingdung.infrastructure.algorithm.feature.names import (
    MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY,
)
from tarakdingdung.infrastructure.algorithm.signal.cross_sectional_momentum import (
    CrossSectionalMomentumSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.signal.moving_average_cross import (
    MovingAverageCrossSignalGenerator,
)
from tests.infrastructure.algorithm.conformance import BTC_IDX, BTC_TKO, ETH_IDX, TS


def features(values) -> FeatureSet:
    return FeatureSet(timestamp=TS, values=values)


def test_momentum_ranks_across_symbols():
    signals = CrossSectionalMomentumSignalGenerator(long_only=False).generate(
        features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {MOMENTUM: 0.1},
                  BTC_TKO: {MOMENTUM: -0.3}}))
    assert signals.scores[BTC_TKO] == pytest.approx(-1.0)
    assert signals.scores[ETH_IDX] == pytest.approx(0.0)
    assert signals.scores[BTC_IDX] == pytest.approx(1.0)


def test_momentum_is_long_only_by_default():
    # Neither venue supports shorting, so a negative weight would describe a
    # position we cannot hold.
    signals = CrossSectionalMomentumSignalGenerator().generate(
        features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {MOMENTUM: -0.3}}))
    assert min(signals.scores.values()) >= 0.0


def test_momentum_ranks_relatively_not_absolutely():
    # All three fell; the least-bad still ranks top, which is what
    # cross-sectional means.
    signals = CrossSectionalMomentumSignalGenerator(long_only=False).generate(
        features({BTC_IDX: {MOMENTUM: -0.1}, ETH_IDX: {MOMENTUM: -0.5},
                  BTC_TKO: {MOMENTUM: -0.9}}))
    assert signals.scores[BTC_IDX] == pytest.approx(1.0)


def test_momentum_handles_a_single_symbol():
    generator = CrossSectionalMomentumSignalGenerator(long_only=False)
    assert generator.generate(features({BTC_IDX: {MOMENTUM: 0.2}})).scores[BTC_IDX] == 1.0
    assert generator.generate(features({BTC_IDX: {MOMENTUM: -0.2}})).scores[BTC_IDX] == -1.0


def test_momentum_handles_no_symbols():
    assert CrossSectionalMomentumSignalGenerator().generate(features({})).scores == {}


def test_momentum_skips_symbols_missing_the_feature():
    signals = CrossSectionalMomentumSignalGenerator().generate(
        features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {VOLATILITY: 0.1}}))
    assert set(signals.scores) == {BTC_IDX}


def test_momentum_reads_a_configured_feature():
    signals = CrossSectionalMomentumSignalGenerator(
        feature=VOLATILITY, long_only=False).generate(
        features({BTC_IDX: {VOLATILITY: 0.9}, ETH_IDX: {VOLATILITY: 0.1}}))
    assert signals.scores[BTC_IDX] == pytest.approx(1.0)


def test_moving_average_cross():
    signals = MovingAverageCrossSignalGenerator().generate(
        features({BTC_IDX: {SMA_FAST: 10.0, SMA_SLOW: 5.0},
                  ETH_IDX: {SMA_FAST: 5.0, SMA_SLOW: 10.0}}))
    assert signals.scores[BTC_IDX] == 1.0
    assert signals.scores[ETH_IDX] == 0.0


def test_moving_average_cross_can_go_short():
    signals = MovingAverageCrossSignalGenerator(long_only=False).generate(
        features({ETH_IDX: {SMA_FAST: 5.0, SMA_SLOW: 10.0}}))
    assert signals.scores[ETH_IDX] == -1.0


def test_moving_average_cross_needs_both_averages():
    signals = MovingAverageCrossSignalGenerator().generate(
        features({BTC_IDX: {SMA_FAST: 10.0}}))
    assert signals.scores == {}
