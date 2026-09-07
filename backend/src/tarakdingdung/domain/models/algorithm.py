import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Symbol

# Weights that sum to one in exact arithmetic often do not in binary floating
# point, so the gross-exposure bound needs a tolerance.
_WEIGHT_TOLERANCE = 1e-9


def _invalid(message: str) -> DomainError:
    return DomainError(message, ErrorType.VALIDATION)


def _check_finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise _invalid(f"{label} must be finite, got {value}")


def _check_positive(value: Decimal, label: str) -> None:
    # ``is_finite`` first: comparing a Decimal NaN raises rather than returning
    # False.
    if not value.is_finite() or value <= 0:
        raise _invalid(f"{label} must be positive, got {value}")


def _check_non_negative(value: Decimal, label: str) -> None:
    if not value.is_finite() or value < 0:
        raise _invalid(f"{label} must be non-negative, got {value}")


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class TimeInForce(StrEnum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTX = "GTX"


class RejectionReason(StrEnum):
    BELOW_MIN_NOTIONAL = "BELOW_MIN_NOTIONAL"
    ROUNDS_TO_ZERO = "ROUNDS_TO_ZERO"
    NO_RULES = "NO_RULES"
    NO_PRICE = "NO_PRICE"


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """Named numeric features per symbol.

    A symbol with too little history to compute a feature is omitted rather
    than filled: an absent key is the normal state at the start of a backtest
    and after every new listing, and it propagates harmlessly downstream.
    """

    timestamp: int
    values: Mapping[Symbol, Mapping[str, float]]

    def __post_init__(self) -> None:
        for symbol, features in self.values.items():
            for name, value in features.items():
                _check_finite(value, f"feature {name!r} of {symbol}")


@dataclass(frozen=True, slots=True)
class Signals:
    """Conviction per symbol in ``[-1, 1]``; an absent symbol means no opinion."""

    timestamp: int
    scores: Mapping[Symbol, float]

    def __post_init__(self) -> None:
        for symbol, score in self.scores.items():
            _check_finite(score, f"signal for {symbol}")
            if not -1.0 <= score <= 1.0:
                raise _invalid(f"signal for {symbol} must lie in [-1, 1], got {score}")


@dataclass(frozen=True, slots=True)
class TargetWeights:
    """Desired portfolio as fractions of equity; the remainder is cash."""

    timestamp: int
    weights: Mapping[Symbol, float]

    def __post_init__(self) -> None:
        gross = 0.0
        for symbol, weight in self.weights.items():
            _check_finite(weight, f"weight for {symbol}")
            gross += abs(weight)
        if gross > 1.0 + _WEIGHT_TOLERANCE:
            raise _invalid(f"gross exposure must not exceed 1, got {gross}")


@dataclass(frozen=True, slots=True)
class TradeIntent:
    """A trade worth making, before venue rules are applied."""

    symbol: Symbol
    side: Side
    quantity: Decimal
    reference_price: Decimal

    def __post_init__(self) -> None:
        _check_positive(self.quantity, "intent quantity")
        _check_positive(self.reference_price, "intent reference price")


@dataclass(frozen=True, slots=True)
class PlannedOrder:
    """An order rounded to a venue's rules and ready to submit."""

    symbol: Symbol
    side: Side
    type: OrderType
    quantity: Decimal
    price: Decimal | None
    time_in_force: TimeInForce
    client_order_id: str | None = None

    def __post_init__(self) -> None:
        _check_positive(self.quantity, "order quantity")
        if self.type is OrderType.MARKET:
            if self.price is not None:
                raise _invalid("market order must not carry a price")
        elif self.price is None:
            raise _invalid(f"{self.type} order requires a price")
        else:
            _check_positive(self.price, "order price")


@dataclass(frozen=True, slots=True)
class RejectedIntent:
    intent: TradeIntent
    reason: RejectionReason


@dataclass(frozen=True, slots=True)
class OrderPlan:
    """Placeable orders and, explicitly, what was dropped and why.

    Rejections are returned rather than discarded: an intent that silently
    vanishes below min-notional is the most common source of unexplained
    live-versus-backtest divergence. Every input intent appears exactly once
    across ``orders`` and ``rejected``.
    """

    orders: tuple[PlannedOrder, ...]
    rejected: tuple[RejectedIntent, ...]


@dataclass(frozen=True, slots=True)
class CyclePlan:
    """Everything one decision cycle concluded, before anything is submitted.

    Produced identically by the live engine and the backtester — they differ
    only in where the snapshot came from and what happens to the orders
    afterwards, which is what keeps the two from drifting apart.

    ``halted_by`` names the first risk rule that flattened the book. Note that
    a halt still produces exit orders: empty target weights mean hold nothing,
    so the rebalancer sells what is held rather than merely declining to buy.
    """

    timestamp: int
    weights: TargetWeights
    orders: OrderPlan
    halted_by: str | None = None

    @property
    def is_halted(self) -> bool:
        return self.halted_by is not None


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """What an order really costs against a given book.

    ``fillable`` is False when the book cannot absorb the order. The honest
    answer is sometimes "not at any price", and a model that returns a number
    regardless flatters every backtest.
    """

    fee: Decimal
    slippage: Decimal
    total: Decimal
    fillable: bool

    def __post_init__(self) -> None:
        _check_non_negative(self.fee, "fee")
        _check_non_negative(self.slippage, "slippage")
