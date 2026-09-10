from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.order import OrderSide


@dataclass(frozen=True, slots=True)
class PlannedOrder:
    symbol_id: str
    side: OrderSide
    quantity: Decimal
    notional: Decimal


@dataclass(frozen=True, slots=True)
class Rejection:
    symbol_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class OrderPlan:
    orders: list[PlannedOrder] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)


class Rebalancer(ABC):
    @abstractmethod
    def rebalance(
        self,
        current: dict[str, Decimal],
        target: list[Weight],
        prices: dict[str, Decimal],
        equity: Decimal,
    ) -> OrderPlan: ...
