from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from tarakdingdung.domain.models.backtest import ValidationRun
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import OverfittingReport


@dataclass(frozen=True, slots=True)
class RunWalkForwardRequest:
    """``parameter_grid`` is the search: one entry per candidate parameter set.

    The grid is explicit rather than generated so that a run records exactly
    what was tried — the overfitting probability is only interpretable
    alongside the number of trials that produced it.
    """

    strategy_id: UUID
    window: TimeRange
    parameter_grid: tuple[dict, ...]
    initial_equity: Decimal
    interval: str = "1h"
    subsets: int = 8
    threshold: float = 0.10
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RunWalkForwardResult:
    validation_id: UUID
    overfitting: OverfittingReport
    best_parameters: dict | None
    trials: int


class StrategyValidation(ABC):
    """Runs a parameter search and judges whether it found an edge or noise.

    Separate from ``Backtesting`` because a backtest is one run over one
    parameter set while this is many runs plus the gate over their collective
    results. Merging them would make the gate an optional flag on a run, and an
    optional gate is not a gate.

    ``best_parameters`` is None when the gate fails. Returning a winner
    alongside a verdict of "this search learned the noise" would invite
    exactly the use the test exists to prevent.
    """

    @abstractmethod
    async def run_walk_forward(self, request: RunWalkForwardRequest) -> RunWalkForwardResult: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> ValidationRun: ...
