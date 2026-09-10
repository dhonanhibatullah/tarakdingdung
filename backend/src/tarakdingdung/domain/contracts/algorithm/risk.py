from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from tarakdingdung.domain.models.decision import Weight


@dataclass(frozen=True, slots=True)
class RiskState:
    equity: Decimal
    daily_pnl: Decimal
    volatility: float
    symbol_venues: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskResult:
    weights: list[Weight]
    halted: bool
    rule: str = ""
    reason: str = ""


class RiskRule(ABC):
    @abstractmethod
    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult: ...


class RiskOverlay(ABC):
    @abstractmethod
    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult: ...
