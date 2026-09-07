"""Tokocrypto v3 trade API client."""
from collections.abc import Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import (
    V3_BASE_URL,
    TokocryptoV3Transport,
    default_now_ms,
)

_DEFAULT_RECV_WINDOW = 5000


class HttpTokocryptoV3TradeApi(TokocryptoV3TradeApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = V3_BASE_URL, recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._t = TokocryptoV3Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)

    async def create_order(self, *, symbol: str, side: str, type: str,
                           quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           price: str | None = None,
                           time_in_force: str | None = None,
                           new_client_order_id: str | None = None,
                           new_order_resp_type: str = "FULL") -> dict:
        return await self._t.signed_request(
            "POST", "/api/v3/order", symbol=symbol, side=side, type=type,
            quantity=quantity, quoteOrderQty=quote_order_qty, price=price,
            timeInForce=time_in_force, newClientOrderId=new_client_order_id,
            newOrderRespType=new_order_resp_type)

    async def query_order(self, *, symbol: str, order_id: int | None = None,
                          orig_client_order_id: str | None = None) -> dict:
        return await self._t.signed_request(
            "GET", "/api/v3/order", symbol=symbol, orderId=order_id,
            origClientOrderId=orig_client_order_id)

    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           orig_client_order_id: str | None = None) -> dict:
        return await self._t.signed_request(
            "DELETE", "/api/v3/order", symbol=symbol, orderId=order_id,
            origClientOrderId=orig_client_order_id)

    async def open_orders(self, *, symbol: str | None = None) -> list:
        return await self._t.signed_request("GET", "/api/v3/openOrders", symbol=symbol)

    async def my_trades(self, *, symbol: str, order_id: int | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, limit: int | None = None) -> list:
        return await self._t.signed_request(
            "GET", "/api/v3/myTrades", symbol=symbol, orderId=order_id,
            startTime=start_time, endTime=end_time, fromId=from_id, limit=limit)

    async def account(self) -> dict:
        return await self._t.signed_request("GET", "/api/v3/account")
