from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from tarakdingdung.domain.models.algorithm import Side
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Symbol


@dataclass(frozen=True, slots=True)
class Fill:
    symbol: Symbol
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal
    timestamp: int


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: int
    equity: Decimal
    # None is the total equity — the series the risk overlay reads. A venue
    # name scopes the point to that venue's holdings.
    venue: str | None = None


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    """How a run actually did.

    Gross and net sit side by side with an explicit ``cost_drag`` so that a
    strategy which looks good before costs and dies after cannot be read as a
    success.
    """

    total_return: float
    sharpe: float
    sortino: float
    max_drawdown: float
    turnover: float
    gross_return: float
    net_return: float
    cost_drag: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class TrialResult:
    """One parameter set's returns, as fed to the overfitting test."""

    label: str
    parameters: Mapping[str, str]
    returns: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class OverfittingReport:
    probability: float
    threshold: float
    passed: bool

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise DomainError(
                f"overfitting probability must lie in [0, 1], got {self.probability}",
                ErrorType.VALIDATION)
