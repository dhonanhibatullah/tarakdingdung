from tarakdingdung.domain.contracts.api.tokocrypto.v1.trade import TokocryptoV1TradeApi
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.algorithm import OrderType, Side, TimeInForce, PlannedOrder
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderRejection, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.execution.live.classify import is_settled
from tarakdingdung.infrastructure.venue.symbols import underscored

# Tokocrypto's /open/v1 encodes these as integers rather than strings.
_SIDES = {Side.BUY: 0, Side.SELL: 1}
_TYPES = {OrderType.LIMIT: 1, OrderType.MARKET: 2, OrderType.LIMIT_MAKER: 7}
_TIME_IN_FORCE = {TimeInForce.GTC: 1, TimeInForce.IOC: 2, TimeInForce.FOK: 3,
                  TimeInForce.GTX: 4}


class TokocryptoLiveExecutor(Executor):
    """Sends real orders to Tokocrypto.

    Unlike Indodax, orders can be looked up by client id alone, so this venue
    can serve the reconciliation path directly.
    """

    _TAG = "execution/tokocrypto"

    def __init__(self, *, trade: TokocryptoV1TradeApi, logger: LeveledLogger) -> None:
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
                                     venue_order_id=str(payload.get("orderId", ""))))

        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=tuple(unconfirmed), fills=())

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        for symbol in symbols:
            payload = await self._trade.all_orders(symbol=underscored(symbol))
            for entry in _rows(payload):
                if entry.get("status") in (0, 1):  # NEW, PARTIALLY_FILLED
                    await self._trade.cancel_order(order_id=_int(entry.get("orderId")),
                                                   client_id=entry.get("clientId"))

    async def read_by_client_order_id(self, client_order_id: str) -> ExecutionResult:
        try:
            payload = await self._trade.query_order(client_id=client_order_id)
        except DomainError as err:
            if err.type is ErrorType.NOT_FOUND:
                # The venue never saw it, so the submission genuinely failed
                # and there is nothing resting to account for.
                return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())
            raise
        return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())

    async def _create(self, order: PlannedOrder, client_order_id: str) -> dict:
        return await self._trade.create_order(
            symbol=underscored(order.symbol), side=_SIDES[order.side],
            type=_TYPES[order.type], quantity=str(order.quantity),
            price=str(order.price) if order.price is not None else None,
            client_id=client_order_id,
            time_in_force=_TIME_IN_FORCE.get(order.time_in_force))


def _rows(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("list"), list):
        return payload["list"]
    return []


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
