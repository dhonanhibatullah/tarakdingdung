from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from tarakdingdung.domain.models.backtest import BacktestRun
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import PerformanceReport


@dataclass(frozen=True, slots=True)
class RunBacktestRequest:
    strategy_id: UUID
    window: TimeRange
    initial_equity: Decimal
    interval: str = "1h"
    periods_per_year: float = 8760.0
    min_completeness: float = 0.99
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RunBacktestResult:
    run_id: UUID
    report: PerformanceReport
    cycles: int
    rejected_orders: int


@dataclass(frozen=True, slots=True)
class ListBacktestsRequest:
    page: int
    limit: int
    strategy_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ListBacktestsResult:
    runs: tuple[BacktestRun, ...]
    total: int


class Backtesting(ABC):
    """Replays stored history through a strategy and scores the result.

    Refuses rather than approximates. A window whose coverage falls below
    ``min_completeness``, or one shorter than the strategy's longest feature
    lookback, raises instead of producing a report: both would yield a
    plausible number from data that cannot support it, and a plausible wrong
    number is more dangerous than an error.

    ``rejected_orders`` is surfaced on the result because a backtest whose
    orders were mostly rejected for min-notional is not the strategy anyone
    thinks they tested.
    """

    @abstractmethod
    async def run(self, request: RunBacktestRequest) -> RunBacktestResult: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> BacktestRun: ...

    @abstractmethod
    async def read_by_pagination(self, request: ListBacktestsRequest) -> ListBacktestsResult: ...
