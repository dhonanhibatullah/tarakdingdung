from abc import ABC, abstractmethod

from tarakdingdung.domain.models.backtest import BacktestResult


class BacktestRepository(ABC):
    @abstractmethod
    async def create(self, entity: BacktestResult) -> BacktestResult: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> BacktestResult | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[BacktestResult], int]: ...
