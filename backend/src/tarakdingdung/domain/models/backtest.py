from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    id: str
    universe_id: str
    from_ms: int
    to_ms: int
    equity_curve: list[Decimal]
    sharpe: float
    max_drawdown: float
    turnover: float
