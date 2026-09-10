from abc import ABC, abstractmethod

from tarakdingdung.domain.models.portfolio import PortfolioSnapshot


class Snapshot(ABC):
    @abstractmethod
    async def take(self) -> PortfolioSnapshot: ...
