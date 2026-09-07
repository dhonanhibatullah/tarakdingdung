from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.models.algorithm import Signals, TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio
from tarakdingdung.infrastructure.algorithm.allocation.selection import selected
from tarakdingdung.infrastructure.algorithm.shared.weights import budget


class EqualWeightAllocator(Allocator):
    """Splits the budget evenly across every symbol with a non-zero signal.

    Conviction decides *whether* to hold, not how much. Equal weighting is the
    honest default when there is no validated reason to believe a stronger
    signal deserves proportionally more capital — and sizing by conviction is
    one of the easier ways to overfit.
    """

    def __init__(self, *, max_gross: float = 1.0,
                 max_positions: int | None = None) -> None:
        self._max_gross = max_gross
        self._max_positions = max_positions

    def allocate(self, signals: Signals, portfolio: Portfolio) -> TargetWeights:
        chosen = selected(signals, self._max_positions)
        if not chosen:
            return TargetWeights(timestamp=signals.timestamp, weights={})
        size = budget(self._max_gross) / len(chosen)
        return TargetWeights(
            timestamp=signals.timestamp,
            weights={symbol: size if score > 0 else -size
                     for symbol, score in chosen})
