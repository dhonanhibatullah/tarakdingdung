from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.contracts.algorithm.feature import FeatureExtractor
from tarakdingdung.domain.contracts.algorithm.signal import SignalGenerator
from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol
from tarakdingdung.domain.models.portfolio import Portfolio

_SAFETY = 1e-12


class PipelineStrategy(Strategy):
    """Chains universe, features, signal and allocation into one strategy.

    The risk overlay deliberately sits *outside* this chain. ``RiskRule`` needs
    a ``RiskState`` — peak equity, daily P&L, trailing volatility — which
    ``Strategy.decide`` does not receive and should not, because that state is
    history the engine owns rather than a fact about the market. Summary 004 §5
    places the risk manager between strategy and executor for the same reason,
    and keeping it there means the overlay applies to every strategy, including
    ones that never use this pipeline.
    """

    def __init__(self, *, universe: UniverseSelector, features: FeatureExtractor,
                 signals: SignalGenerator, allocator: Allocator) -> None:
        self._universe = universe
        self._features = features
        self._signals = signals
        self._allocator = allocator

    def decide(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> TargetWeights:
        eligible = self._universe.select(snapshot)
        features = self._features.compute(_restricted(snapshot, eligible))
        return self._allocator.allocate(self._signals.generate(features), portfolio)


class BuyAndHoldStrategy(Strategy):
    """The control every strategy has to beat after costs.

    The research is blunt that most published methods do not beat it, so it is
    not a formality — it is the null hypothesis, and it is here so that a
    backtest cannot quietly omit it.
    """

    def __init__(self, symbols: tuple[Symbol, ...], *, max_gross: float = 1.0) -> None:
        self._symbols = symbols
        self._max_gross = max_gross

    def decide(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> TargetWeights:
        tradable = [s for s in self._symbols if s in snapshot.last_prices]
        if not tradable:
            return TargetWeights(timestamp=snapshot.timestamp, weights={})
        size = (self._max_gross - _SAFETY) / len(tradable)
        return TargetWeights(timestamp=snapshot.timestamp,
                             weights={s: size for s in tradable})


def _restricted(snapshot: MarketSnapshot, symbols: tuple[Symbol, ...]) -> MarketSnapshot:
    """Narrow a snapshot to the eligible universe.

    Restricting here rather than filtering later means a symbol excluded by the
    universe cannot influence a cross-sectional ranking, which it otherwise
    would by shifting everything else's rank.
    """
    keep = frozenset(symbols)
    return MarketSnapshot(
        timestamp=snapshot.timestamp,
        candles={s: c for s, c in snapshot.candles.items() if s in keep},
        books={s: b for s, b in snapshot.books.items() if s in keep},
        last_prices={s: p for s, p in snapshot.last_prices.items() if s in keep},
    )
