from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from tarakdingdung.domain.models.market import Symbol, Venue


@dataclass(frozen=True, slots=True)
class Position:
    symbol: Symbol
    quantity: Decimal
    average_price: Decimal


@dataclass(frozen=True, slots=True)
class Portfolio:
    """Holdings at a point in time.

    ``cash`` is keyed by venue because it genuinely is: IDR sitting on Indodax
    cannot buy anything on Tokocrypto, and moving it takes real time. A single
    pooled balance would let a backtest place trades the live engine cannot.
    """

    timestamp: int
    cash: Mapping[Venue, Decimal]
    positions: Mapping[Symbol, Position]
    equity: Decimal


@dataclass(frozen=True, slots=True)
class RiskState:
    """History-derived inputs to the risk overlay.

    Kept apart from ``Portfolio``, which is a point-in-time fact, so that the
    drawdown and volatility rules stay pure functions of what they are handed.
    """

    timestamp: int
    equity_peak: Decimal
    daily_pnl: Decimal
    realized_volatility: float
    halted: bool
