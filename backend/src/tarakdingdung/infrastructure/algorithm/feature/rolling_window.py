from tarakdingdung.domain.contracts.algorithm.feature import FeatureExtractor
from tarakdingdung.domain.models.algorithm import FeatureSet
from tarakdingdung.domain.models.market import MarketSnapshot
from tarakdingdung.infrastructure.algorithm.feature.names import (
    MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY,
)
from tarakdingdung.infrastructure.algorithm.shared import statistics


class RollingWindowFeatureExtractor(FeatureExtractor):
    """Momentum, two moving averages and realised volatility per symbol.

    A symbol whose history is shorter than the longest window is omitted
    entirely rather than computed from a partial window: a 30-day average over
    four days is not a shorter average, it is a different and misleading
    number.
    """

    def __init__(self, *, momentum_window: int = 30, fast_window: int = 10,
                 slow_window: int = 30, volatility_window: int = 30) -> None:
        self._momentum = momentum_window
        self._fast = fast_window
        self._slow = slow_window
        self._volatility = volatility_window
        self._required = max(momentum_window, fast_window, slow_window,
                             volatility_window) + 1

    def compute(self, snapshot: MarketSnapshot) -> FeatureSet:
        values = {}
        for symbol, candles in snapshot.candles.items():
            if len(candles) < self._required:
                continue
            features = self._features([float(c.close) for c in candles])
            if features is not None:
                values[symbol] = features
        return FeatureSet(timestamp=snapshot.timestamp, values=values)

    def _features(self, closes: list[float]) -> dict[str, float] | None:
        base = closes[-1 - self._momentum]
        if base <= 0:
            return None
        returns = statistics.simple_returns(closes[-self._volatility - 1:])
        return {
            MOMENTUM: closes[-1] / base - 1.0,
            SMA_FAST: statistics.mean(closes[-self._fast:]),
            SMA_SLOW: statistics.mean(closes[-self._slow:]),
            VOLATILITY: statistics.stdev(returns),
        }
