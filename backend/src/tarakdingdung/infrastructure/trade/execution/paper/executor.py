import uuid
from decimal import Decimal

from tarakdingdung.domain.contracts.trade.executor import ExecutionResult, Executor
from tarakdingdung.domain.contracts.trade.exchange import Exchange
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.order import Fill, Order
from tarakdingdung.domain.models.symbol import Symbol


class PaperExecutor(Executor):
    def __init__(self, exchange: Exchange, clock: Clock) -> None:
        self._exchange = exchange
        self._clock = clock

    async def submit(
        self, orders: list[Order], symbols: dict[str, Symbol]
    ) -> ExecutionResult:
        now = self._clock.now_ms()
        fills: list[Fill] = []
        for order in orders:
            symbol = symbols.get(order.symbol_id)
            if symbol is None:
                continue
            await self._exchange.place_order(
                symbol, order.side, order.quantity, order.price, order.client_order_id
            )
            fills.append(
                Fill(
                    id=str(uuid.uuid4()),
                    order_id=order.id,
                    price=order.price,
                    quantity=order.quantity,
                    fee=Decimal("0"),
                    filled_at_ms=now,
                )
            )
        return ExecutionResult(unconfirmed=[], fills=fills)
