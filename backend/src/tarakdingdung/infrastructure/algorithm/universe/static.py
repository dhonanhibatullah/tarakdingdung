from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol
from tarakdingdung.infrastructure.algorithm.shared.ordering import symbol_key


class StaticUniverseSelector(UniverseSelector):
    """A pinned list, filtered to what the snapshot actually carries.

    The v1 universe is a deliberate choice rather than a discovered one, so
    this is the baseline. Symbols absent from the snapshot are dropped instead
    of raising: a venue outage should shrink the universe, not stop the engine.
    """

    def __init__(self, symbols: tuple[Symbol, ...]) -> None:
        self._symbols = frozenset(symbols)

    def select(self, snapshot: MarketSnapshot) -> tuple[Symbol, ...]:
        return tuple(sorted(
            (s for s in self._symbols if s in snapshot.last_prices),
            key=symbol_key))
