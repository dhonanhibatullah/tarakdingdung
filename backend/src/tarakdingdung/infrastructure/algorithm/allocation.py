from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.models.algorithm import Signals, TargetWeights
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.portfolio import Portfolio

# Guards the gross bound against binary floating-point summation error, which
# would otherwise reject a fully-invested book as leveraged.
_SAFETY = 1e-12


def _ordering(symbol: Symbol) -> tuple[str, str, str]:
    return (symbol.venue, symbol.base, symbol.quote)


def _selected(signals: Signals, max_positions: int | None) -> list[tuple[Symbol, float]]:
    held = [(s, v) for s, v in signals.scores.items() if v != 0.0]
    if max_positions is None:
        return sorted(held, key=lambda item: _ordering(item[0]))
    ranked = sorted(held, key=lambda item: (-abs(item[1]), _ordering(item[0])))
    return sorted(ranked[:max_positions], key=lambda item: _ordering(item[0]))


class EqualWeightAllocator(Allocator):
    """Splits the budget evenly across every symbol with a non-zero signal.

    Conviction decides *whether* to hold, not how much. Equal weighting is the
    honest default when there is no validated reason to believe a stronger
    signal deserves proportionally more capital — and the research is that
    sizing by conviction is one of the easier ways to overfit.
    """

    def __init__(self, *, max_gross: float = 1.0,
                 max_positions: int | None = None) -> None:
        self._max_gross = max_gross
        self._max_positions = max_positions

    def allocate(self, signals: Signals, portfolio: Portfolio) -> TargetWeights:
        selected = _selected(signals, self._max_positions)
        if not selected:
            return TargetWeights(timestamp=signals.timestamp, weights={})
        size = (self._max_gross - _SAFETY) / len(selected)
        weights = {symbol: size if score > 0 else -size
                   for symbol, score in selected}
        return TargetWeights(timestamp=signals.timestamp, weights=weights)


class ConvictionWeightedAllocator(Allocator):
    """Sizes in proportion to the absolute signal, normalised to the budget.

    Included as the counterpart to equal weighting so the two can be compared
    on the same backtest rather than argued about.
    """

    def __init__(self, *, max_gross: float = 1.0,
                 max_positions: int | None = None) -> None:
        self._max_gross = max_gross
        self._max_positions = max_positions

    def allocate(self, signals: Signals, portfolio: Portfolio) -> TargetWeights:
        selected = _selected(signals, self._max_positions)
        total = sum(abs(score) for _, score in selected)
        if not selected or total <= 0:
            return TargetWeights(timestamp=signals.timestamp, weights={})
        budget = self._max_gross - _SAFETY
        weights = {symbol: budget * score / total for symbol, score in selected}
        return TargetWeights(timestamp=signals.timestamp, weights=weights)
