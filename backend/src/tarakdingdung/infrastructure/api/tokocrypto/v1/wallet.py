from collections.abc import Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v1.wallet import TokocryptoV1WalletApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.transport import (
    BASE_URL,
    TokocryptoV1Transport,
    default_now_ms,
)

_DEFAULT_RECV_WINDOW = 5000


class HttpTokocryptoV1WalletApi(TokocryptoV1WalletApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = BASE_URL, recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._t = TokocryptoV1Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)

    async def withdraw(self, *, asset: str, address: str, amount: str,
                       network: str | None = None, address_tag: str | None = None,
                       client_id: str | None = None) -> dict:
        return await self._t.signed_post("/open/v1/withdraws", asset=asset, address=address,
                                         amount=amount, network=network,
                                         addressTag=address_tag, clientId=client_id)

    async def withdraw_history(self, *, asset: str | None = None, status: int | None = None,
                               from_id: int | None = None, start_time: int | None = None,
                               end_time: int | None = None) -> dict:
        return await self._t.signed_get("/open/v1/withdraws", asset=asset, status=status,
                                        fromId=from_id, startTime=start_time,
                                        endTime=end_time)

    async def deposit_history(self, *, asset: str | None = None, status: int | None = None,
                              from_id: int | None = None, start_time: int | None = None,
                              end_time: int | None = None) -> dict:
        return await self._t.signed_get("/open/v1/deposits", asset=asset, status=status,
                                        fromId=from_id, startTime=start_time,
                                        endTime=end_time)

    async def deposit_address(self, *, asset: str, network: str) -> dict:
        return await self._t.signed_get("/open/v1/deposits/address", asset=asset,
                                        network=network)
