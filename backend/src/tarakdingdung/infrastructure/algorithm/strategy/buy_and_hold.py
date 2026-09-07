from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol
from tarakdingdung.domain.models.portfolio import Portfolio
from tarakdingdung.infrastructure.algorithm.shared.weights import budget


class BuyAndHoldStrategy(Strategy):
    """The control every strategy has to beat after costs.

    The research is blunt that most published methods do not beat it, so it is
    not a formality — it is the null hypothesis, and it is here so that a
    backtest cannot quietly omit it.
    """

    def __init__(self, symbols: tuple[Symbol, ...], *,
                 max_gross: float = 1.0) -> None:
        self._symbols = symbols
        self._max_gross = max_gross

    def decide(self, snapshot: MarketSnapshot,
               portfolio: Portfolio) -> TargetWeights:
        tradable = [s for s in self._symbols if s in snapshot.last_prices]
        if not tradable:
            return TargetWeights(timestamp=snapshot.timestamp, weights={})
        size = budget(self._max_gross) / len(tradable)
        return TargetWeights(timestamp=snapshot.timestamp,
                             weights={s: size for s in tradable})
