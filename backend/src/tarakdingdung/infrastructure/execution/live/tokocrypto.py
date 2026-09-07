"""Live order execution for Tokocrypto over the Binance-standard `/api/v3` API."""
from decimal import Decimal

from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderRejection, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.performance import Fill
from tarakdingdung.infrastructure.execution.live.classify import is_settled
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import joined_upper

_VENUE = "tokocrypto"
_SIDES = {Side.BUY: "BUY", Side.SELL: "SELL"}
_TYPES = {OrderType.LIMIT: "LIMIT", OrderType.MARKET: "MARKET",
          OrderType.LIMIT_MAKER: "LIMIT_MAKER"}
_TIME_IN_FORCE = {TimeInForce.GTC: "GTC", TimeInForce.IOC: "IOC", TimeInForce.FOK: "FOK"}

_EMPTY = ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())


class TokocryptoLiveExecutor(Executor):
    """Sends real orders to Tokocrypto via the Binance-standard `/api/v3` API.

    `create_order` is sent with `newOrderRespType=FULL`, so a crossing order
    comes back with a `fills` array this maps straight to `Fill`s. A fill whose
    commission was charged in an asset other than the quote currency records a
    zero fee and a warning: a BNB-denominated number must not enter a
    quote-denominated ledger.
    """

    _TAG = "execution/tokocrypto"

    def __init__(self, *, trade: TokocryptoV3TradeApi, logger: LeveledLogger) -> None:
        self._trade = trade
        self._logger = logger

    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult:
        accepted: list[OrderAck] = []
        rejected: list[OrderRejection] = []
        unconfirmed: list[UnconfirmedOrder] = []
        fills: list[Fill] = []

        for order in orders:
            client_order_id = order.client_order_id or ""
            try:
                payload = await self._create(order, client_order_id)
            except DomainError as err:
                await self._logger.error(f"{self._TAG}/Submit", "order failed",
                                         {"err": err, "client_order_id": client_order_id})
                if is_settled(err.type):
                    rejected.append(OrderRejection(
                        order=order, client_order_id=client_order_id, reason=err.message))
                else:
                    unconfirmed.append(UnconfirmedOrder(
                        order=order, client_order_id=client_order_id, reason=err.message))
                continue
            accepted.append(OrderAck(order=order, client_order_id=client_order_id,
                                     venue_order_id=str(payload.get("orderId", ""))))
            fills.extend(await self._fills(order, payload))

        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=tuple(unconfirmed), fills=tuple(fills))

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        for symbol in symbols:
            resting = await self._trade.open_orders(symbol=joined_upper(symbol))
            for entry in resting or []:
                await self._trade.cancel_order(
                    symbol=joined_upper(symbol),
                    order_id=entry.get("orderId"),
                    orig_client_order_id=entry.get("clientOrderId"))

    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        if symbol is None:
            raise DomainError("tokocrypto v3 order lookup needs a symbol",
                              ErrorType.UNIMPLEMENTED)
        try:
            await self._trade.query_order(symbol=joined_upper(symbol),
                                          orig_client_order_id=client_order_id)
        except DomainError as err:
            if err.type is ErrorType.NOT_FOUND:
                return _EMPTY
            raise
        # The venue knows the order. Back-filling its state and fills from the
        # payload / my_trades is a known gap; the portfolio sync reconciles
        # holdings against the venue in the meantime.
        return _EMPTY

    async def _create(self, order: PlannedOrder, client_order_id: str) -> dict:
        # Binance rejects `timeInForce` on anything but a plain LIMIT order
        # (-1106), so it is only sent for OrderType.LIMIT.
        time_in_force: str | None = None
        if order.type is OrderType.LIMIT:
            if order.time_in_force is TimeInForce.GTX:
                raise DomainError(
                    "tokocrypto v3 has no timeInForce for GTX; use "
                    "OrderType.LIMIT_MAKER",
                    ErrorType.BAD_ARGS)
            time_in_force = _TIME_IN_FORCE.get(order.time_in_force)
        return await self._trade.create_order(
            symbol=joined_upper(order.symbol), side=_SIDES[order.side],
            type=_TYPES[order.type], quantity=str(order.quantity),
            price=str(order.price) if order.price is not None else None,
            time_in_force=time_in_force,
            new_client_order_id=client_order_id, new_order_resp_type="FULL")

    async def _fills(self, order: PlannedOrder, payload: dict) -> list[Fill]:
        try:
            timestamp = int(payload.get("transactTime") or 0)
        except (TypeError, ValueError):
            timestamp = 0
        quote = order.symbol.quote.upper()
        out: list[Fill] = []
        for entry in payload.get("fills") or []:
            try:
                asset = (entry.get("commissionAsset") or "").upper()
                if asset != quote:
                    await self._logger.warn(
                        f"{self._TAG}/Submit", "fee charged in a foreign asset",
                        {"client_order_id": order.client_order_id,
                         "commission_asset": asset, "quote": quote})
                fee = (to_decimal(entry.get("commission"), "commission", venue=_VENUE,
                                  default=Decimal(0))
                       if asset == quote else Decimal(0))
                fill = Fill(
                    symbol=order.symbol, side=order.side,
                    quantity=to_decimal(entry.get("qty"), "fill qty", venue=_VENUE),
                    price=to_decimal(entry.get("price"), "fill price", venue=_VENUE),
                    fee=fee, timestamp=timestamp)
            except (DomainError, ValueError, TypeError) as err:
                await self._logger.error(
                    f"{self._TAG}/Submit", "unparseable fill row",
                    {"client_order_id": order.client_order_id, "err": err})
                continue
            out.append(fill)
        return out
