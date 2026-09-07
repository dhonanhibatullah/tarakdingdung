from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.models.market import Candle, OrderBook, Symbol, SymbolRules


class MarketDataSource(ABC):
    """A venue's market data, in domain terms.

    The raw API clients return the venue's own JSON shapes. Something has to
    turn those into ``Candle`` and ``OrderBook``, and it must not be the
    usecase: a collector that parsed exchange payloads would need changing
    every time either venue altered a field name, and would be untestable
    without fixtures of two different JSON dialects.

    One implementation per venue, wrapping that venue's clients.
    """

    @abstractmethod
    async def fetch_candles(self, *, symbol: Symbol, interval: str,
                            limit: int) -> tuple[Candle, ...]: ...

    @abstractmethod
    async def fetch_book(self, *, symbol: Symbol, limit: int) -> OrderBook: ...

    @abstractmethod
    async def fetch_price(self, *, symbol: Symbol) -> Decimal: ...

    @abstractmethod
    async def fetch_rules(self) -> Mapping[Symbol, SymbolRules]: ...
