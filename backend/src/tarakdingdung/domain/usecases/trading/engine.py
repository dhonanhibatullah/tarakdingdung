from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class CycleStatus(str, Enum):
    DISABLED = "disabled"
    SKIPPED = "skipped"
    NO_DATA = "no_data"
    HELD = "held"
    HALTED = "halted"
    EXECUTED = "executed"


@dataclass(frozen=True, slots=True)
class CycleResult:
    status: CycleStatus
    detail: str = ""


class TradingEngine(ABC):
    @abstractmethod
    async def run_cycle(self) -> CycleResult: ...

    @abstractmethod
    async def dry_run(self) -> CycleResult: ...
