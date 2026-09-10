from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tarakdingdung.domain.models.order import Order, OrderStatus
from tarakdingdung.domain.models.symbol import Symbol


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    resolved: list[tuple[str, OrderStatus]] = field(default_factory=list)
    still_unconfirmed: list[str] = field(default_factory=list)


class Reconciler(ABC):
    @abstractmethod
    async def reconcile(
        self, orders: list[Order], symbols: dict[str, Symbol]
    ) -> ReconcileResult: ...
