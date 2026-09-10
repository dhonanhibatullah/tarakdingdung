from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PLANNED = "planned"
    SUBMITTED = "submitted"
    UNCONFIRMED = "unconfirmed"
    FILLED = "filled"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    client_order_id: str
    symbol_id: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    status: OrderStatus
    created_at_ms: int


@dataclass(frozen=True, slots=True)
class Fill:
    id: str
    order_id: str
    price: Decimal
    quantity: Decimal
    fee: Decimal
    filled_at_ms: int
