from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from tarakdingdung.domain.models.portfolio import Balance


@dataclass(frozen=True, slots=True)
class PortfolioView:
    venue: str
    as_of_ms: int
    equity: Decimal
    balances: list[Balance]


class Portfolio(ABC):
    @abstractmethod
    async def read(self, venue: str) -> PortfolioView | None: ...
