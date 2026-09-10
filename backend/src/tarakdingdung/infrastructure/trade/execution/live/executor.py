from tarakdingdung.domain.contracts.trade.exchange import Exchange
from tarakdingdung.domain.contracts.trade.executor import ExecutionResult, Executor
from tarakdingdung.domain.models.order import Order
from tarakdingdung.domain.models.symbol import Symbol


class LiveExecutor(Executor):
    def __init__(self, exchange: Exchange) -> None:
        self._exchange = exchange

    async def submit(
        self, orders: list[Order], symbols: dict[str, Symbol]
    ) -> ExecutionResult:
        unconfirmed: list[str] = []
        for order in orders:
            symbol = symbols.get(order.symbol_id)
            if symbol is None:
                unconfirmed.append(order.client_order_id)
                continue
            try:
                await self._exchange.place_order(
                    symbol, order.side, order.quantity, order.price, order.client_order_id
                )
            except Exception:
                unconfirmed.append(order.client_order_id)
        return ExecutionResult(unconfirmed=unconfirmed, fills=[])
