from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.execution import Discrepancy
from tarakdingdung.domain.models.market import TimeRange, Venue
from tarakdingdung.domain.models.performance import EquityPoint
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


@dataclass(frozen=True, slots=True)
class SyncRequest:
    """``venues`` empty means every configured venue."""

    venues: tuple[Venue, ...] = ()


@dataclass(frozen=True, slots=True)
class SyncResult:
    portfolio: Portfolio
    discrepancies: tuple[Discrepancy, ...]
    unreachable: tuple[Venue, ...]


@dataclass(frozen=True, slots=True)
class CurrentPortfolioResult:
    portfolio: Portfolio
    risk_state: RiskState


@dataclass(frozen=True, slots=True)
class EquityCurveRequest:
    window: TimeRange


@dataclass(frozen=True, slots=True)
class EquityCurveResult:
    points: tuple[EquityPoint, ...]


class PortfolioSync(ABC):
    """Reconciles what we think we hold against what the venues say.

    A ``Portfolio`` is not free: it is assembled from both venues' account
    endpoints and cannot be assumed from our own order history, because fills
    happen that we did not initiate — a partial fill we recorded wrongly, a
    manual trade, a venue-side liquidation.

    ``discrepancies`` is returned rather than raised because it is the single
    most valuable thing this can report, and an exception in a cron becomes a
    log line nobody reads. A caller that ignores it is choosing to size against
    a portfolio that does not exist.

    ``unreachable`` is separate from an empty result: not knowing a venue's
    balance is different from knowing it is zero.
    """

    @abstractmethod
    async def sync(self, request: SyncRequest) -> SyncResult: ...

    @abstractmethod
    async def read_current(self) -> CurrentPortfolioResult: ...

    @abstractmethod
    async def read_equity_curve(self, request: EquityCurveRequest) -> EquityCurveResult: ...
