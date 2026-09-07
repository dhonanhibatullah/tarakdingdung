from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from tarakdingdung.domain.models.algorithm import OrderPlan, TargetWeights
from tarakdingdung.domain.models.execution import ExecutionResult


class CycleDecision(StrEnum):
    """Why a cycle ended the way it did.

    "The bot did nothing" is the most common operational question and the
    hardest to answer afterwards, so every outcome is distinguishable: no
    drift is not no data, and a halt is not a skip.
    """

    TRADED = "TRADED"
    NO_DRIFT = "NO_DRIFT"
    HALTED = "HALTED"
    NO_DATA = "NO_DATA"
    DISABLED = "DISABLED"
    SKIPPED = "SKIPPED"
    DRY_RUN = "DRY_RUN"


@dataclass(frozen=True, slots=True)
class RunCycleRequest:
    strategy_id: UUID
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class RunCycleResult:
    timestamp: int
    strategy_id: UUID
    decision: CycleDecision
    weights: TargetWeights | None = None
    plan: OrderPlan | None = None
    execution: ExecutionResult | None = None
    halted_by: str | None = None
    reconciled: int = 0


class TradingEngine(ABC):
    """One decision-and-act pass over one strategy.

    A single step, not a loop: cadence, retries and overlap belong to the cron
    adapter that drives it. That keeps the usecase ignorant of time, which is
    what lets a test drive it one step at a time with no clock.

    The ordering it must follow, and why:

    - planned orders are persisted **before** submission, so a process that
      dies mid-submit leaves a reconcilable record rather than orders at the
      venue that nothing knows about;
    - a submission that fails in transport is recorded unconfirmed and **never
      retried** — the order may already exist, and a blind retry turns one
      intended position into two;
    - a tripped risk rule cancels resting orders before returning, because a
      halt that only stops placing new orders leaves the old ones working;
    - a failed cancellation during a halt escalates: the halt flag persists and
      every later cycle re-attempts it, so the failure gets louder rather than
      quieter.

    ``dry_run`` plans without persisting or submitting, so an operator can ask
    what the engine would do without touching the market.
    """

    @abstractmethod
    async def run_cycle(self, request: RunCycleRequest) -> RunCycleResult: ...
