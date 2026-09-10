from decimal import Decimal

from tarakdingdung.domain.contracts.trade.exchange import (
    Account,
    AccountBalance,
    Exchange,
    OrderResult,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.order import OrderSide
from tarakdingdung.domain.models.symbol import Symbol


class PaperExchange(Exchange):
    def __init__(self, balances: dict[str, Decimal] | None = None) -> None:
        self._balances = {k: v for k, v in (balances or {}).items()}
        self._locked = {k: Decimal("0") for k in self._balances}
        self._orders: dict[str, OrderResult] = {}

    async def account(self) -> Account:
        return Account(
            balances=[
                AccountBalance(
                    asset=asset,
                    free=self._balances.get(asset, Decimal("0")),
                    locked=self._locked.get(asset, Decimal("0")),
                )
                for asset in self._balances
            ]
        )

    async def place_order(
        self,
        symbol: Symbol,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        client_order_id: str,
    ) -> OrderResult:
        cost = quantity * price
        if side is OrderSide.BUY:
            self._balances[symbol.quote] = self._balances.get(symbol.quote, Decimal("0")) - cost
            self._balances[symbol.base] = self._balances.get(symbol.base, Decimal("0")) + quantity
        else:
            self._balances[symbol.base] = self._balances.get(symbol.base, Decimal("0")) - quantity
            self._balances[symbol.quote] = self._balances.get(symbol.quote, Decimal("0")) + cost
        result = OrderResult(
            order_id=client_order_id,
            client_order_id=client_order_id,
            status="FILLED",
            filled_quantity=quantity,
        )
        self._orders[client_order_id] = result
        return result

    async def get_order(self, symbol: Symbol, order_id: str) -> OrderResult:
        result = self._orders.get(order_id)
        if result is None:
            raise DomainError("order not found", ErrorType.NOT_FOUND)
        return result

    async def cancel_order(self, symbol: Symbol, order_id: str) -> None:
        self._orders.pop(order_id, None)
