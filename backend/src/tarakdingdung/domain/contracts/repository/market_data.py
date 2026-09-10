from abc import ABC, abstractmethod

from tarakdingdung.domain.models.market import Candle


class MarketDataRepository(ABC):
    @abstractmethod
    async def append_candles(self, candles: list[Candle]) -> None: ...

    @abstractmethod
    async def read_range(
        self, symbol_id: str, from_ms: int, to_ms: int
    ) -> list[Candle]: ...

    @abstractmethod
    async def read_latest(self, symbol_id: str) -> Candle | None: ...

    @abstractmethod
    async def read_coverage(self, symbol_id: str) -> tuple[int, int] | None: ...
