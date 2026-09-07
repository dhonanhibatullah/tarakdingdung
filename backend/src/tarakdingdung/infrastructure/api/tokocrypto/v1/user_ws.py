from collections.abc import AsyncIterator, Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v1.user_ws import TokocryptoUserWebSocket
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.shared.websocket import ReconnectingWebSocket
from tarakdingdung.infrastructure.api.tokocrypto.v1.transport import (
    BASE_URL,
    TokocryptoV1Transport,
    default_now_ms,
)

_STREAM_URL = "wss://stream-cloud.tokocrypto.site/stream"
_DEFAULT_RECV_WINDOW = 5000


class WsTokocryptoUserWebSocket(TokocryptoUserWebSocket):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = BASE_URL, stream_url: str = _STREAM_URL,
                 recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms,
                 logger: LeveledLogger | None = None) -> None:
        self._t = TokocryptoV1Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)
        self._stream_url = stream_url
        self._logger = logger

    async def _listen_url(self) -> str:
        data = await self._t.signed_post("/open/v1/user-listen-token")
        token = None
        if isinstance(data, dict):
            token = data.get("listenToken") or data.get("listenKey") or data.get("token")
        if not token:
            raise DomainError("tokocrypto.ws.user: no listen token in response",
                              ErrorType.UPSTREAM)
        return f"{self._stream_url}?streams={token}"

    async def stream(self) -> AsyncIterator[dict]:
        socket = ReconnectingWebSocket(self._listen_url, tag="tokocrypto.ws.user",
                                       logger=self._logger)
        async for message in socket.messages():
            yield message
