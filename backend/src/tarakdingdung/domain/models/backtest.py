from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import (
    OverfittingReport, PerformanceReport, TrialResult,
)


@dataclass(frozen=True, slots=True)
class BacktestRun:
    """One replay of one strategy configuration over one window."""

    id: UUID
    strategy_id: UUID
    window: TimeRange
    initial_equity: Decimal
    report: PerformanceReport
    created_at: datetime
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ValidationRun:
    """A parameter search and the overfitting verdict on it.

    Holds every trial, not only the winner: the whole point of the PBO test is
    that the winner cannot be judged except against the ones it beat.
    """

    id: UUID
    strategy_id: UUID
    window: TimeRange
    trials: tuple[TrialResult, ...]
    overfitting: OverfittingReport
    created_at: datetime
    created_by: UUID | None = None
