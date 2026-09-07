from tarakdingdung.domain.contracts.api.indodax.v2.trade import IndodaxV2TradeApi
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.algorithm import OrderType, PlannedOrder
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderRejection, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.execution.live.classify import is_settled
from tarakdingdung.infrastructure.venue.symbols import underscored

# Errors the venue decided about: the order definitely did not open, so it is a
# rejection. Anything else — a timeout, a 5xx, a dropped connection — leaves
# the outcome unknown and must be reported unconfirmed instead.
_DECIDED = frozenset({ErrorType.BAD_ARGS, ErrorType.VALIDATION, ErrorType.CONFLICT,
                      ErrorType.NOT_FOUND, ErrorType.FORBIDDEN,
                      ErrorType.UNAUTHORIZED})


class IndodaxLiveExecutor(Executor):
    """Sends real orders to Indodax.

    Orders are submitted one at a time and each failure is classified rather
    than lumped together. That distinction is the entire safety story: a
    rejection is settled and needs nothing, while an unknown outcome must be
    reconciled by client order id and never retried.
    """

    _TAG = "execution/indodax"

    def __init__(self, *, trade: IndodaxV2TradeApi, logger: LeveledLogger) -> None:
        self._trade = trade
        self._logger = logger

    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult:
        accepted: list[OrderAck] = []
        rejected: list[OrderRejection] = []
        unconfirmed: list[UnconfirmedOrder] = []

        for order in orders:
            client_order_id = order.client_order_id or ""
            try:
                payload = await self._create(order, client_order_id)
            except DomainError as err:
                await self._logger.error(f"{self._TAG}/Submit", "order failed",
                                         {"err": err, "client_order_id": client_order_id})
                if is_settled(err.type):
                    rejected.append(OrderRejection(
                        order=order, client_order_id=client_order_id,
                        reason=err.message))
                else:
                    unconfirmed.append(UnconfirmedOrder(
                        order=order, client_order_id=client_order_id,
                        reason=err.message))
                continue
            accepted.append(OrderAck(order=order, client_order_id=client_order_id,
                                     venue_order_id=str(payload.get("order_id", ""))))

        # Fills are not reported here: Indodax acknowledges an order without
        # telling us what filled. Fills arrive through reconciliation and the
        # portfolio sync, which read the venue rather than guessing.
        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=tuple(unconfirmed), fills=())

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        for symbol in symbols:
            resting = await self._trade.open_orders(symbol=underscored(symbol))
            for entry in resting or []:
                await self._trade.cancel_order(
                    symbol=underscored(symbol),
                    order_id=_int(entry.get("order_id")),
                    client_order_id=entry.get("client_order_id"))

    async def read_by_client_order_id(self, client_order_id: str) -> ExecutionResult:
        raise DomainError(
            "indodax order lookup requires a symbol; reconcile through the "
            "journal, which records it alongside the client order id",
            ErrorType.UNIMPLEMENTED)

    async def _create(self, order: PlannedOrder, client_order_id: str) -> dict:
        return await self._trade.create_order(
            symbol=underscored(order.symbol), side=str(order.side).lower(),
            type=_ORDER_TYPES[order.type],
            price=str(order.price) if order.price is not None else None,
            quantity=str(order.quantity), new_client_order_id=client_order_id,
            time_in_force=str(order.time_in_force))


_ORDER_TYPES = {OrderType.MARKET: "market", OrderType.LIMIT: "limit",
                OrderType.LIMIT_MAKER: "limit"}


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
