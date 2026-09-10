from abc import ABC, abstractmethod

from tarakdingdung.domain.models.market import Candle, Ticker
from tarakdingdung.domain.models.symbol import Symbol


class MarketSource(ABC):
    @abstractmethod
    async def fetch_candles(
        self, symbol: Symbol, interval: str, from_ms: int, to_ms: int
    ) -> list[Candle]: ...

    @abstractmethod
    async def fetch_ticker(self, symbol: Symbol) -> Ticker: ...
