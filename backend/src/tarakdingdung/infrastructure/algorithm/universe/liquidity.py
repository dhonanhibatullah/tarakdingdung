from collections.abc import Sequence
from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.models.market import BookLevel, MarketSnapshot, Symbol
from tarakdingdung.infrastructure.algorithm.shared.ordering import symbol_key


class LiquidityUniverseSelector(UniverseSelector):
    """Admits symbols whose book is deep enough to trade out of.

    Depth is measured as the notional resting within ``depth_levels`` of the
    top of book on the *thinner* side, because a symbol we can enter but not
    exit is worse than one we never entered. Thin IDR books are a named risk
    in the research, which is why this is a block rather than an assumption.
    """

    def __init__(self, *, min_book_notional: Decimal,
                 depth_levels: int = 10) -> None:
        self._min_notional = min_book_notional
        self._levels = depth_levels

    def select(self, snapshot: MarketSnapshot) -> tuple[Symbol, ...]:
        eligible = (
            symbol for symbol, book in snapshot.books.items()
            if symbol in snapshot.last_prices
            and min(self._notional(book.bids),
                    self._notional(book.asks)) >= self._min_notional)
        return tuple(sorted(eligible, key=symbol_key))

    def _notional(self, levels: Sequence[BookLevel]) -> Decimal:
        return sum((lv.price * lv.quantity for lv in levels[:self._levels]),
                   Decimal(0))
