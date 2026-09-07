from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from tarakdingdung.domain.models.backtest import BacktestRun, ValidationRun
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import (
    OverfittingReport, PerformanceReport, TrialResult,
)


class BacktestRepository(ABC):
    """Backtest and validation results.

    Runs are kept rather than recomputed because the overfitting test is a
    judgement about a *search*: how many parameter sets were tried, and how the
    winner ranked against the ones it beat. A repository that stored only the
    best run would destroy the evidence the gate depends on.
    """

    @abstractmethod
    async def create_run(self, *, strategy_id: UUID, window: TimeRange,
                         initial_equity: Decimal, report: PerformanceReport,
                         created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_run_by_id(self, id: UUID) -> BacktestRun | None: ...

    @abstractmethod
    async def read_runs_by_pagination(self, *, page: int, limit: int,
                                      strategy_id: UUID | None) -> tuple[list[BacktestRun], int]: ...

    @abstractmethod
    async def create_validation(self, *, strategy_id: UUID, window: TimeRange,
                                trials: tuple[TrialResult, ...],
                                overfitting: OverfittingReport,
                                created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_validation_by_id(self, id: UUID) -> ValidationRun | None: ...

    @abstractmethod
    async def read_validations_by_pagination(
            self, *, page: int, limit: int,
            strategy_id: UUID | None) -> tuple[list[ValidationRun], int]: ...
