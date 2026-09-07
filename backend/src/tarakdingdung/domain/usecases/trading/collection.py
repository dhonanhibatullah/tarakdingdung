from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.execution import CollectionFailure
from tarakdingdung.domain.models.market import Symbol


@dataclass(frozen=True, slots=True)
class CollectRequest:
    """``symbols`` empty means every symbol in every enabled strategy's
    universe, which is what the cron passes."""

    symbols: tuple[Symbol, ...] = ()
    interval: str = "1h"
    include_books: bool = True


@dataclass(frozen=True, slots=True)
class CollectResult:
    timestamp: int
    collected: tuple[Symbol, ...]
    candles_written: int
    failed: tuple[CollectionFailure, ...]


class MarketDataCollection(ABC):
    """Pulls market data from the venues into storage.

    Failure is partial and returned, never raised: one venue being unreachable
    must shrink a poll rather than abort it, because aborting would leave the
    *other* venue's history permanently gapped for the same interval. Nothing
    downstream can be built or tested without accumulated data, so the
    collector's job is to lose as little of it as possible.
    """

    @abstractmethod
    async def collect(self, request: CollectRequest) -> CollectResult: ...
