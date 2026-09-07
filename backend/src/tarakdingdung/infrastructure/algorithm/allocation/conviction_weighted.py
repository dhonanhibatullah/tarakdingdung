from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.models.algorithm import Signals, TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio
from tarakdingdung.infrastructure.algorithm.allocation.selection import selected
from tarakdingdung.infrastructure.algorithm.shared.weights import budget


class ConvictionWeightedAllocator(Allocator):
    """Sizes in proportion to the absolute signal, normalised to the budget.

    The counterpart to equal weighting, here so the two can be compared on the
    same backtest rather than argued about.
    """

    def __init__(self, *, max_gross: float = 1.0,
                 max_positions: int | None = None) -> None:
        self._max_gross = max_gross
        self._max_positions = max_positions

    def allocate(self, signals: Signals, portfolio: Portfolio) -> TargetWeights:
        chosen = selected(signals, self._max_positions)
        total = sum(abs(score) for _, score in chosen)
        if not chosen or total <= 0:
            return TargetWeights(timestamp=signals.timestamp, weights={})
        share = budget(self._max_gross) / total
        return TargetWeights(
            timestamp=signals.timestamp,
            weights={symbol: share * score for symbol, score in chosen})
