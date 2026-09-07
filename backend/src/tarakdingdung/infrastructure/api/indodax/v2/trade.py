import time
from collections.abc import Callable
from typing import Any

import httpx

from tarakdingdung.domain.contracts.api.indodax.v2.trade import IndodaxV2TradeApi
from tarakdingdung.infrastructure.api.indodax.errors import raise_v2_error
from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256

_BASE_URL = "https://api.indodax.com"


def _default_now_ms() -> int:
    return int(time.time() * 1000)


class HttpIndodaxV2TradeApi(IndodaxV2TradeApi):
    """`https://api.indodax.com/api/v2/*` — signed with HMAC-SHA256 over the
    urlencoded param string (query for GET/DELETE, body for POST).
    """

    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = _BASE_URL, recv_window: int = 5000,
                 now_ms: Callable[[], int] = _default_now_ms) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="indodax.v2")
        self._api_key = api_key
        self._secret_key = secret_key
        self._recv_window = recv_window
        self._now_ms = now_ms

    async def _call(self, http_method: str, path: str, **params: Any) -> Any:
        encoded = encode_params({
            "timestamp": self._now_ms(),
            "recvWindow": self._recv_window,
            **params,
        })
        headers = {
            "Accept": "application/json",
            "X-APIKEY": self._api_key,
            "Sign": hmac_sha256(self._secret_key, encoded),
        }
        if http_method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = await self._rest.request("POST", path, body=encoded, headers=headers)
        else:
            payload = await self._rest.request(http_method, path, query=encoded,
                                               headers=headers)
        raise_v2_error(payload)
        return payload

    async def create_order(self, *, symbol: str, side: str, type: str,
                           price: str | None = None, quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           new_client_order_id: str | None = None,
                           time_in_force: str | None = None,
                           self_trade_prevention_mode: str | None = None) -> dict:
        return await self._call(
            "POST", "/api/v2/order", symbol=symbol, side=side, type=type, price=price,
            quantity=quantity, quoteOrderQty=quote_order_qty,
            newClientOrderId=new_client_order_id, timeInForce=time_in_force,
            selfTradePreventionMode=self_trade_prevention_mode,
        )

    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           client_order_id: str | None = None) -> dict:
        return await self._call("DELETE", "/api/v2/order", symbol=symbol, orderId=order_id,
                                clientOrderId=client_order_id)

    async def open_orders(self, *, symbol: str | None = None) -> list:
        return await self._call("GET", "/api/v2/openOrders", symbol=symbol)

    async def get_order(self, *, symbol: str, order_id: int | None = None,
                        client_order_id: str | None = None) -> dict:
        return await self._call("GET", "/api/v2/order", symbol=symbol, orderId=order_id,
                                clientOrderId=client_order_id)

    async def account(self, *, omit_zero_balances: bool | None = None) -> dict:
        return await self._call("GET", "/api/v2/account", omitZeroBalances=omit_zero_balances)

    async def order_histories(self, *, symbol: str | None = None, limit: int | None = None,
                              start_time: int | None = None,
                              end_time: int | None = None) -> list:
        return await self._call("GET", "/api/v2/order/histories", symbol=symbol, limit=limit,
                                startTime=start_time, endTime=end_time)

    async def my_trades(self, *, symbol: str, limit: int | None = None,
                        start_time: int | None = None,
                        end_time: int | None = None) -> list:
        return await self._call("GET", "/api/v2/myTrades", symbol=symbol, limit=limit,
                                startTime=start_time, endTime=end_time)

    async def withdraw_history(self, *, coin: str | None = None, limit: int | None = None,
                               start_time: int | None = None, end_time: int | None = None,
                               withdraw_status: str | None = None) -> list:
        return await self._call("GET", "/api/v2/capital/withdraw/history", coin=coin,
                                limit=limit, startTime=start_time, endTime=end_time,
                                WithdrawStatus=withdraw_status)

    async def deposit_history(self, *, coin: str | None = None,
                              start_time: int | None = None,
                              end_time: int | None = None) -> list:
        return await self._call("GET", "/api/v2/capital/deposit/hisrec", coin=coin,
                                startTime=start_time, endTime=end_time)

    async def deposit_address_list(self) -> list:
        return await self._call("GET", "/api/v2/capital/deposit/address/list")

    async def fiat_orders(self, *, start_time: int | None = None,
                          end_time: int | None = None) -> list:
        return await self._call("GET", "/api/v2/fiat/orders", startTime=start_time,
                                endTime=end_time)

    async def withdraw_coin(self, *, asset: str, amount: str, address: str | None = None,
                            username: str | None = None,
                            network: str | None = None) -> dict:
        return await self._call("POST", "/api/v2/capital/withdraw/apply", asset=asset,
                                amount=amount, address=address, username=username,
                                network=network)

    async def withdraw_fiat(self, *, amount: str, bank_account_id: str) -> dict:
        return await self._call("POST", "/api/v2/fiat/withdraw", amount=amount,
                                bankAccountId=bank_account_id)
