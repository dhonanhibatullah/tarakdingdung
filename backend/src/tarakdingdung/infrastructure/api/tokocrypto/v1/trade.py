from collections.abc import Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v1.trade import TokocryptoV1TradeApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.transport import (
    BASE_URL,
    TokocryptoV1Transport,
    default_now_ms,
)

_DEFAULT_RECV_WINDOW = 5000


class HttpTokocryptoV1TradeApi(TokocryptoV1TradeApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = BASE_URL, recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._t = TokocryptoV1Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)

    async def create_order(self, *, symbol: str, side: int, type: int,
                           quantity: str | None = None, quote_order_qty: str | None = None,
                           price: str | None = None, stop_price: str | None = None,
                           iceberg_qty: str | None = None, client_id: str | None = None,
                           time_in_force: int | None = None,
                           self_trade_prevention_mode: int | None = None) -> dict:
        return await self._t.signed_post(
            "/open/v1/orders", symbol=symbol, side=side, type=type, quantity=quantity,
            quoteOrderQty=quote_order_qty, price=price, stopPrice=stop_price,
            icebergQty=iceberg_qty, clientId=client_id, timeInForce=time_in_force,
            selfTradePreventionMode=self_trade_prevention_mode,
        )

    async def query_order(self, *, order_id: int | None = None,
                          client_id: str | None = None) -> dict:
        return await self._t.signed_get("/open/v1/orders/detail", orderId=order_id,
                                        clientId=client_id)

    async def cancel_order(self, *, order_id: int | None = None,
                           client_id: str | None = None) -> dict:
        return await self._t.signed_post("/open/v1/orders/cancel", orderId=order_id,
                                         clientId=client_id)

    async def all_orders(self, *, symbol: str, type: int | None = None,
                         side: int | None = None, start_time: int | None = None,
                         end_time: int | None = None, from_id: str | None = None,
                         direct: str | None = None, limit: int | None = None) -> dict:
        return await self._t.signed_get(
            "/open/v1/orders", symbol=symbol, type=type, side=side, startTime=start_time,
            endTime=end_time, fromId=from_id, direct=direct, limit=limit,
        )

    async def create_oco(self, *, symbol: str, side: int, quantity: str, price: str,
                         stop_price: str, stop_limit_price: str,
                         list_client_id: str | None = None,
                         limit_client_id: str | None = None,
                         stop_client_id: str | None = None) -> dict:
        return await self._t.signed_post(
            "/open/v1/orders/oco", symbol=symbol, side=side, quantity=quantity, price=price,
            stopPrice=stop_price, stopLimitPrice=stop_limit_price,
            listClientId=list_client_id, limitClientId=limit_client_id,
            stopClientId=stop_client_id,
        )

    async def my_trades(self, *, symbol: str, order_id: str | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, direct: str | None = None,
                        limit: int | None = None) -> dict:
        return await self._t.signed_get(
            "/open/v1/orders/trades", symbol=symbol, orderId=order_id, startTime=start_time,
            endTime=end_time, fromId=from_id, direct=direct, limit=limit,
        )

    async def account(self) -> dict:
        return await self._t.signed_get("/open/v1/account/spot")

    async def account_asset(self, *, asset: str) -> dict:
        return await self._t.signed_get("/open/v1/account/spot/asset", asset=asset)
