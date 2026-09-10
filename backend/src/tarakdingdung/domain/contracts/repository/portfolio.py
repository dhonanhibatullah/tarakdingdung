from abc import ABC, abstractmethod

from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot


class PortfolioRepository(ABC):
    @abstractmethod
    async def create_snapshot(
        self, snapshot: PortfolioSnapshot, balances: list[Balance]
    ) -> PortfolioSnapshot: ...

    @abstractmethod
    async def read_latest(self, venue: str) -> PortfolioSnapshot | None: ...

    @abstractmethod
    async def read_balances(self, snapshot_id: str) -> list[Balance]: ...
