from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol


def _sorted(symbols: set[Symbol]) -> tuple[Symbol, ...]:
    # Deterministic ordering: downstream blocks break ties by position, so an
    # unstable universe would make a backtest irreproducible.
    return tuple(sorted(symbols, key=lambda s: (s.venue, s.base, s.quote)))


class StaticUniverseSelector(UniverseSelector):
    """A pinned list, filtered to what the snapshot actually carries.

    The v1 universe is a deliberate choice rather than a discovered one, so
    this is the baseline. Symbols absent from the snapshot are dropped instead
    of raising: a venue outage should shrink the universe, not stop the engine.
    """

    def __init__(self, symbols: tuple[Symbol, ...]) -> None:
        self._symbols = frozenset(symbols)

    def select(self, snapshot: MarketSnapshot) -> tuple[Symbol, ...]:
        return _sorted({s for s in self._symbols if s in snapshot.last_prices})


class LiquidityUniverseSelector(UniverseSelector):
    """Admits symbols whose book is deep enough to trade out of.

    Depth is measured as the notional resting within ``depth_levels`` of the
    top of book on the thinner side. Thin IDR books are a named risk, and a
    symbol we cannot exit is worse than one we never entered.
    """

    def __init__(self, *, min_book_notional: Decimal,
                 depth_levels: int = 10) -> None:
        self._min_notional = min_book_notional
        self._levels = depth_levels

    def select(self, snapshot: MarketSnapshot) -> tuple[Symbol, ...]:
        eligible = set()
        for symbol, book in snapshot.books.items():
            if symbol not in snapshot.last_prices:
                continue
            bid = self._notional(book.bids)
            ask = self._notional(book.asks)
            if min(bid, ask) >= self._min_notional:
                eligible.add(symbol)
        return _sorted(eligible)

    def _notional(self, levels) -> Decimal:
        return sum((lv.price * lv.quantity for lv in levels[:self._levels]),
                   Decimal(0))
