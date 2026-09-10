from decimal import Decimal

from tarakdingdung.domain.models.market import Candle
from tarakdingdung.infrastructure.algorithm.backtest.weights import (
    equal_weight,
    momentum_top_k,
)


def _candles(closes):
    return [
        Candle(
            symbol_id="s",
            open_time_ms=i,
            open=Decimal(str(c)),
            high=Decimal(str(c)),
            low=Decimal(str(c)),
            close=Decimal(str(c)),
            volume=Decimal("1"),
        )
        for i, c in enumerate(closes)
    ]


def test_equal_weight_sums_to_one():
    weights = equal_weight(["a", "b", "c", "d"])
    assert sum(w.weight for w in weights) == 1.0
    assert all(w.weight == 0.25 for w in weights)


def test_equal_weight_empty():
    assert equal_weight([]) == []


def test_momentum_selects_top_k():
    candles = {
        "up": _candles([1, 2, 3, 4, 5]),
        "flat": _candles([1, 1, 1, 1, 1]),
        "down": _candles([5, 4, 3, 2, 1]),
    }
    weights = momentum_top_k(candles, top_k=2, lookback=2)
    assert [w.symbol_id for w in weights] == ["up", "flat"]


def test_momentum_ignores_short_series():
    candles = {"short": _candles([1, 2])}
    assert momentum_top_k(candles, top_k=1, lookback=2) == []
