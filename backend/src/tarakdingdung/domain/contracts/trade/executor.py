from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tarakdingdung.domain.models.order import Fill, Order
from tarakdingdung.domain.models.symbol import Symbol


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    unconfirmed: list[str] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)


class Executor(ABC):
    @abstractmethod
    async def submit(
        self, orders: list[Order], symbols: dict[str, Symbol]
    ) -> ExecutionResult: ...
