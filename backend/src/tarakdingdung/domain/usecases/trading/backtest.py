from abc import ABC, abstractmethod

from tarakdingdung.domain.models.backtest import BacktestResult


class Backtest(ABC):
    @abstractmethod
    async def replay(
        self, universe_id: str, from_ms: int, to_ms: int
    ) -> BacktestResult: ...
