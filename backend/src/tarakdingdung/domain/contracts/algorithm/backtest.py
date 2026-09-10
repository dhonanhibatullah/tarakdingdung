from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.order import Fill


@dataclass(frozen=True, slots=True)
class RebalanceEvent:
    timestamp_ms: int
    target: list[Weight]
    prices: dict[str, Decimal]


@dataclass(frozen=True, slots=True)
class FillSimResult:
    equity_curve: list[Decimal] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0


class FillSimulator(ABC):
    @abstractmethod
    def simulate(
        self,
        events: list[RebalanceEvent],
        rebalancer: Rebalancer,
        cost_model: CostModel,
        initial_equity: Decimal,
    ) -> FillSimResult: ...
