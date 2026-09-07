from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.models.market import (
    Candle, Coverage, MarketSnapshot, OrderBook, Symbol, TimeRange,
)


class MarketDataRepository(ABC):
    """Stored market history.

    The read methods are the only source a backtest or a live cycle has, so
    they carry the obligation ``MarketSnapshot`` documents: never return a
    datum stamped after the requested instant, and omit stale data rather than
    carrying it.
    """

    @abstractmethod
    async def write_candles(self, *, symbol: Symbol, interval: str,
                            candles: tuple[Candle, ...]) -> int: ...

    @abstractmethod
    async def write_book(self, book: OrderBook) -> None: ...

    @abstractmethod
    async def write_price(self, *, symbol: Symbol, timestamp: int,
                          price: Decimal) -> None: ...

    @abstractmethod
    async def read_candles(self, *, symbol: Symbol, interval: str,
                           window: TimeRange,
                           limit: int | None = None) -> tuple[Candle, ...]: ...

    @abstractmethod
    async def read_book(self, *, symbol: Symbol,
                        as_of: int) -> OrderBook | None: ...

    @abstractmethod
    async def read_prices(self, *, symbols: tuple[Symbol, ...], as_of: int,
                          max_age: int) -> Mapping[Symbol, Decimal]:
        """Last price per symbol at ``as_of``, omitting anything older than
        ``max_age``. Omission is the point: a stale price looks valid and will
        size a real order."""
        ...

    @abstractmethod
    async def read_snapshot(self, *, symbols: tuple[Symbol, ...], as_of: int,
                            interval: str, lookback: int,
                            max_age: int) -> MarketSnapshot: ...

    @abstractmethod
    async def read_coverage(self, *, symbol: Symbol, interval: str,
                            window: TimeRange) -> Coverage: ...
