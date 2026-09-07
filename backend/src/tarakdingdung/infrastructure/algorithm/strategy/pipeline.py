from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.contracts.algorithm.feature import FeatureExtractor
from tarakdingdung.domain.contracts.algorithm.signal import SignalGenerator
from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol
from tarakdingdung.domain.models.portfolio import Portfolio


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

    def decide(self, snapshot: MarketSnapshot,
               portfolio: Portfolio) -> TargetWeights:
        eligible = self._universe.select(snapshot)
        features = self._features.compute(_restricted(snapshot, eligible))
        return self._allocator.allocate(self._signals.generate(features), portfolio)


def _restricted(snapshot: MarketSnapshot,
                symbols: tuple[Symbol, ...]) -> MarketSnapshot:
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
