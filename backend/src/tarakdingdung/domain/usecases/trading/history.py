from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.market import (
    Candle, Coverage, MarketSnapshot, Symbol, TimeRange,
)


@dataclass(frozen=True, slots=True)
class ReadCandlesRequest:
    symbol: Symbol
    interval: str
    window: TimeRange
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class ReadCandlesResult:
    symbol: Symbol
    interval: str
    candles: tuple[Candle, ...]


@dataclass(frozen=True, slots=True)
class ReadSnapshotRequest:
    symbols: tuple[Symbol, ...]
    as_of: int
    interval: str = "1h"
    lookback: int = 200
    max_age_ms: int = 3_600_000


@dataclass(frozen=True, slots=True)
class ReadCoverageRequest:
    symbol: Symbol
    interval: str
    window: TimeRange


class MarketDataHistory(ABC):
    """Reads stored market data.

    Split from collection because the two have opposite obligations: the
    collector tolerates missing data, while this must never invent it. It
    serves both the HTTP surface and the engine, and the snapshot it builds is
    the lookahead boundary the whole algorithm layer depends on.
    """

    @abstractmethod
    async def read_candles(self, request: ReadCandlesRequest) -> ReadCandlesResult: ...

    @abstractmethod
    async def read_snapshot(self, request: ReadSnapshotRequest) -> MarketSnapshot: ...

    @abstractmethod
    async def read_coverage(self, request: ReadCoverageRequest) -> Coverage: ...
