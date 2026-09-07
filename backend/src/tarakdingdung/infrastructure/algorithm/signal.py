from tarakdingdung.domain.contracts.algorithm.signal import SignalGenerator
from tarakdingdung.domain.models.algorithm import FeatureSet, Signals
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.algorithm.feature import MOMENTUM, SMA_FAST, SMA_SLOW


def _ordering(symbol: Symbol) -> tuple[str, str, str]:
    return (symbol.venue, symbol.base, symbol.quote)


class CrossSectionalMomentumSignalGenerator(SignalGenerator):
    """Ranks symbols against each other and maps the ranking onto [-1, 1].

    Ranking rather than the raw feature because the cross-sectional decision is
    "which of these is strongest", and a rank is immune to the outliers and
    scale shifts that make raw momentum incomparable across regimes.

    ``long_only`` clips negative scores to zero. It defaults to true because
    neither Indodax nor Tokocrypto exposes a way to short: a negative weight
    would describe a position we cannot hold.
    """

    def __init__(self, *, feature: str = MOMENTUM, long_only: bool = True) -> None:
        self._feature = feature
        self._long_only = long_only

    def generate(self, features: FeatureSet) -> Signals:
        present = [(symbol, values[self._feature])
                   for symbol, values in features.values.items()
                   if self._feature in values]
        return Signals(timestamp=features.timestamp,
                       scores=self._score(present))

    def _score(self, present: list[tuple[Symbol, float]]) -> dict[Symbol, float]:
        if not present:
            return {}
        if len(present) == 1:
            symbol, value = present[0]
            return {symbol: self._clip(1.0 if value > 0 else -1.0)}
        # Ties break on symbol identity so the ranking is reproducible.
        ranked = sorted(present, key=lambda item: (item[1], _ordering(item[0])))
        last = len(ranked) - 1
        return {symbol: self._clip(2.0 * index / last - 1.0)
                for index, (symbol, _) in enumerate(ranked)}

    def _clip(self, score: float) -> float:
        return max(0.0, score) if self._long_only else score


class MovingAverageCrossSignalGenerator(SignalGenerator):
    """The control from summary 004 Phase 3: fast average above slow is long.

    Deliberately crude. Its job is to be the bar a real strategy has to clear
    after costs, and the research is clear that most do not clear it.
    """

    def __init__(self, *, long_only: bool = True) -> None:
        self._long_only = long_only

    def generate(self, features: FeatureSet) -> Signals:
        scores = {}
        for symbol, values in features.values.items():
            if SMA_FAST not in values or SMA_SLOW not in values:
                continue
            score = 1.0 if values[SMA_FAST] > values[SMA_SLOW] else -1.0
            scores[symbol] = max(0.0, score) if self._long_only else score
        return Signals(timestamp=features.timestamp, scores=scores)
