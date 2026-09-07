import pytest

from tarakdingdung.infrastructure.algorithm.feature.names import (
    MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY,
)
from tarakdingdung.infrastructure.algorithm.feature.rolling_window import (
    RollingWindowFeatureExtractor,
)
from tests.infrastructure.algorithm.conformance import BTC_IDX, ETH_IDX
from tests.infrastructure.algorithm.fixtures import candles, snapshot


def _extractor(**kwargs) -> RollingWindowFeatureExtractor:
    defaults = dict(momentum_window=4, fast_window=2, slow_window=4,
                    volatility_window=4)
    return RollingWindowFeatureExtractor(**{**defaults, **kwargs})


def test_omits_symbols_with_too_little_history():
    features = _extractor(momentum_window=5, slow_window=5,
                          volatility_window=5).compute(snapshot(candle_map={
        BTC_IDX: candles([100.0] * 10),
        ETH_IDX: candles([100.0] * 3),
    }))
    assert BTC_IDX in features.values
    assert ETH_IDX not in features.values


def test_computes_the_documented_features():
    prices = [100.0, 101.0, 102.0, 103.0, 110.0]
    values = _extractor().compute(
        snapshot(candle_map={BTC_IDX: candles(prices)})).values[BTC_IDX]
    assert set(values) == {MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY}
    assert values[MOMENTUM] == pytest.approx(110.0 / 100.0 - 1.0)
    assert values[SMA_FAST] == pytest.approx((103.0 + 110.0) / 2)
    assert values[SMA_SLOW] == pytest.approx((101.0 + 102.0 + 103.0 + 110.0) / 4)
    assert values[VOLATILITY] > 0


def test_volatility_is_zero_for_a_flat_series():
    values = _extractor().compute(
        snapshot(candle_map={BTC_IDX: candles([100.0] * 6)})).values[BTC_IDX]
    assert values[VOLATILITY] == 0.0
    assert values[MOMENTUM] == 0.0


def test_omits_a_symbol_whose_momentum_base_is_zero():
    # The base is the close N candles back; a zero there would divide by
    # nothing, so the symbol is omitted rather than made infinite.
    features = _extractor(momentum_window=2, slow_window=2,
                          volatility_window=2).compute(
        snapshot(candle_map={BTC_IDX: candles([0.0, 1.0, 2.0])}))
    assert BTC_IDX not in features.values


def test_uses_only_the_most_recent_window():
    # Ancient history outside the window must not move the averages.
    short = _extractor().compute(
        snapshot(candle_map={BTC_IDX: candles([1.0, 1.0, 100.0, 101.0, 102.0, 103.0, 110.0])}))
    assert short.values[BTC_IDX][SMA_FAST] == pytest.approx((103.0 + 110.0) / 2)
