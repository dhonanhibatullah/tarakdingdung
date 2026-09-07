from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


class PortfolioRepository(ABC):
    """What we hold and how it has been doing.

    ``read_risk_state`` is derived rather than stored raw: peak equity, daily
    P&L and trailing volatility are functions of the equity curve, and
    recomputing them from history keeps them consistent with what the reports
    show. Storing them separately would let the two disagree.
    """

    @abstractmethod
    async def write_snapshot(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    async def read_latest(self, *, as_of: int) -> Portfolio | None: ...

    @abstractmethod
    async def read_risk_state(self, *, as_of: int,
                              venue: str | None = None) -> RiskState: ...

    @abstractmethod
    async def write_equity_point(self, point: EquityPoint) -> None: ...

    @abstractmethod
    async def read_equity_curve(self, *, window: TimeRange,
                                venue: str | None = None) -> tuple[EquityPoint, ...]: ...

    @abstractmethod
    async def append_fills(self, fills: tuple[Fill, ...]) -> None: ...

    @abstractmethod
    async def read_fills(self, *, window: TimeRange) -> tuple[Fill, ...]: ...

    @abstractmethod
    async def set_halt(self, *, strategy_id: UUID, halted: bool,
                       reason: str | None) -> None: ...

    @abstractmethod
    async def read_halt(self, *, strategy_id: UUID) -> tuple[bool, str | None]: ...
