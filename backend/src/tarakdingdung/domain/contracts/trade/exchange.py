from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from tarakdingdung.domain.models.order import OrderSide
from tarakdingdung.domain.models.symbol import Symbol


@dataclass(frozen=True, slots=True)
class AccountBalance:
    asset: str
    free: Decimal
    locked: Decimal


@dataclass(frozen=True, slots=True)
class Account:
    balances: list[AccountBalance]


@dataclass(frozen=True, slots=True)
class OrderResult:
    order_id: str
    client_order_id: str
    status: str
    filled_quantity: Decimal


class Exchange(ABC):
    @abstractmethod
    async def account(self) -> Account: ...

    @abstractmethod
    async def place_order(
        self,
        symbol: Symbol,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        client_order_id: str,
    ) -> OrderResult: ...

    @abstractmethod
    async def get_order(self, symbol: Symbol, order_id: str) -> OrderResult: ...

    @abstractmethod
    async def cancel_order(self, symbol: Symbol, order_id: str) -> None: ...
