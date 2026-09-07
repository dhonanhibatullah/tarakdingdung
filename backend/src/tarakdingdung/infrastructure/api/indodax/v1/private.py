import time
from collections.abc import Callable
from typing import Any

import httpx

from tarakdingdung.domain.contracts.api.indodax.v1.private import IndodaxV1PrivateApi
from tarakdingdung.infrastructure.api.indodax.errors import raise_v1_error
from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha512

_BASE_URL = "https://indodax.com"


def _default_now_ms() -> int:
    return int(time.time() * 1000)


class HttpIndodaxV1PrivateApi(IndodaxV1PrivateApi):
    """`POST https://indodax.com/tapi` — signed with HMAC-SHA512 over the
    urlencoded request body; unwraps ``return`` on ``success == 1``.
    """

    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = _BASE_URL, recv_window: int = 5000,
                 now_ms: Callable[[], int] = _default_now_ms) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="indodax.v1.private")
        self._api_key = api_key
        self._secret_key = secret_key
        self._recv_window = recv_window
        self._now_ms = now_ms

    async def _call(self, method: str, **params: Any) -> Any:
        body = encode_params({
            "method": method,
            "timestamp": self._now_ms(),
            "recvWindow": self._recv_window,
            **params,
        })
        headers = {
            "Key": self._api_key,
            "Sign": hmac_sha512(self._secret_key, body),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = await self._rest.request("POST", "/tapi", body=body, headers=headers)
        raise_v1_error(payload)
        return payload.get("return", payload) if isinstance(payload, dict) else payload

    async def get_info(self) -> dict:
        return await self._call("getInfo")

    async def trans_history(self, *, start: str | None = None,
                            end: str | None = None) -> dict:
        return await self._call("transHistory", start=start, end=end)

    async def trade(self, *, pair: str, type: str, price: str | None = None,
                    idr: str | None = None, coin_amount: str | None = None,
                    order_type: str | None = None, client_order_id: str | None = None,
                    time_in_force: str | None = None,
                    smp_cancel: str | None = None) -> dict:
        coin = pair.split("_", 1)[0]
        return await self._call(
            "trade", pair=pair, type=type, price=price, idr=idr,
            order_type=order_type, client_order_id=client_order_id,
            time_in_force=time_in_force, smp_cancel=smp_cancel,
            **({coin: coin_amount} if coin_amount is not None else {}),
        )

    async def trade_history(self, *, pair: str, count: int | None = None,
                            from_id: int | None = None, end_id: int | None = None,
                            order: str | None = None, since: int | None = None,
                            end: int | None = None, order_id: int | None = None) -> dict:
        return await self._call("tradeHistory", pair=pair, count=count, from_id=from_id,
                                end_id=end_id, order=order, since=since, end=end,
                                order_id=order_id)

    async def open_orders(self, *, pair: str | None = None) -> dict:
        return await self._call("openOrders", pair=pair)

    async def order_history(self, *, pair: str, count: int | None = None,
                            from_: int | None = None) -> dict:
        return await self._call("orderHistory", pair=pair, count=count, **{"from": from_})

    async def get_order(self, *, pair: str, order_id: int) -> dict:
        return await self._call("getOrder", pair=pair, order_id=order_id)

    async def get_order_by_client_order_id(self, *, client_order_id: str) -> dict:
        return await self._call("getOrderByClientOrderId", client_order_id=client_order_id)

    async def cancel_order(self, *, pair: str, order_id: int, type: str,
                           order_type: str | None = None) -> dict:
        return await self._call("cancelOrder", pair=pair, order_id=order_id, type=type,
                                order_type=order_type)

    async def cancel_by_client_order_id(self, *, client_order_id: str) -> dict:
        return await self._call("cancelByClientOrderId", client_order_id=client_order_id)

    async def withdraw_fee(self, *, currency: str, network: str | None = None) -> dict:
        return await self._call("withdrawFee", currency=currency, network=network)

    async def withdraw_coin(self, *, currency: str, withdraw_amount: str, request_id: str,
                            network: str | None = None, withdraw_address: str | None = None,
                            withdraw_memo: str | None = None,
                            withdraw_input_method: str | None = None,
                            withdraw_username: str | None = None) -> dict:
        return await self._call(
            "withdrawCoin", currency=currency, withdraw_amount=withdraw_amount,
            request_id=request_id, network=network, withdraw_address=withdraw_address,
            withdraw_memo=withdraw_memo, withdraw_input_method=withdraw_input_method,
            withdraw_username=withdraw_username,
        )

    async def list_downline(self, *, page: int, limit: int) -> dict:
        return await self._call("listDownline", page=page, limit=limit)

    async def check_downline(self, *, email: str) -> dict:
        return await self._call("checkDownline", email=email)

    async def create_voucher(self, *, amount: int, to_email: str) -> dict:
        return await self._call("createVoucher", amount=amount, to_email=to_email)
