from tarakdingdung.domain.contracts.algorithm.signal import SignalGenerator
from tarakdingdung.domain.models.algorithm import FeatureSet, Signals
from tarakdingdung.infrastructure.algorithm.feature.names import SMA_FAST, SMA_SLOW


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
