from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.models.algorithm import PlannedOrder, Side
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderRejection,
)
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.performance import Fill


class PaperExecutor(Executor):
    """Simulates fills against the real book, without sending anything.

    Prices come from the stored order book and are charged through the same
    ``CostModel`` a backtest uses, so paper results stay comparable to backtest
    results and to each other. An order the book cannot absorb is *rejected*
    rather than filled at an invented price — the divergence between paper and
    live should come from latency and queue position, not from pretending
    liquidity exists.

    Nothing here can fail in transport, so it never returns unconfirmed orders.
    That is the one place paper legitimately differs from live, and it is why
    the reconciliation path still needs exercising against a real venue before
    Phase 6.
    """

    _TAG = "execution/paper"

    def __init__(self, *, market_data: MarketDataRepository, cost_model: CostModel,
                 clock: Clock) -> None:
        self._market_data = market_data
        self._cost_model = cost_model
        self._clock = clock

    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult:
        now = await self._clock.now_ms()
        accepted: list[OrderAck] = []
        rejected: list[OrderRejection] = []
        fills: list[Fill] = []

        for index, order in enumerate(orders):
            client_order_id = order.client_order_id or ""
            book = await self._market_data.read_book(symbol=order.symbol, as_of=now)
            if book is None:
                rejected.append(OrderRejection(
                    order=order, client_order_id=client_order_id,
                    reason="no order book available"))
                continue

            estimate = self._cost_model.estimate(order, book)
            if not estimate.fillable:
                rejected.append(OrderRejection(
                    order=order, client_order_id=client_order_id,
                    reason="insufficient book depth"))
                continue

            price = self._fill_price(order, book)
            accepted.append(OrderAck(order=order, client_order_id=client_order_id,
                                     venue_order_id=f"paper-{now}-{index}"))
            fills.append(Fill(symbol=order.symbol, side=order.side,
                              quantity=order.quantity, price=price,
                              fee=estimate.fee, timestamp=now))

        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=(), fills=tuple(fills))

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        # Paper orders fill or reject immediately, so nothing ever rests.
        return None

    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())

    @staticmethod
    def _fill_price(order: PlannedOrder, book) -> Decimal:
        levels = book.asks if order.side is Side.BUY else book.bids
        if order.price is not None:
            return order.price
        return levels[0].price if levels else Decimal(0)
