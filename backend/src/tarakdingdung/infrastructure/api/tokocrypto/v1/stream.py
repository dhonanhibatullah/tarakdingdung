from collections.abc import Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v1.stream import TokocryptoV1StreamApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.transport import (
    BASE_URL,
    TokocryptoV1Transport,
    default_now_ms,
)

_DEFAULT_RECV_WINDOW = 5000


class HttpTokocryptoV1StreamApi(TokocryptoV1StreamApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = BASE_URL, recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._t = TokocryptoV1Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)

    async def create_listen_token(self, *, validity: int | None = None) -> dict:
        return await self._t.signed_post("/open/v1/user-listen-token", validity=validity)
