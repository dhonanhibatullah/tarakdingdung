import json
from collections.abc import AsyncIterator, Sequence

import websockets

from tarakdingdung.domain.contracts.api.tokocrypto.v1.market_ws import (
    TokocryptoMarketWebSocket,
)
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.infrastructure.api.shared.websocket import ReconnectingWebSocket

_URL = "wss://stream-cloud.tokocrypto.site/stream"


class WsTokocryptoMarketWebSocket(TokocryptoMarketWebSocket):
    def __init__(self, *, url: str = _URL, logger: LeveledLogger | None = None) -> None:
        self._url = url
        self._logger = logger

    async def stream(self, streams: Sequence[str]) -> AsyncIterator[dict]:
        async def on_open(ws: websockets.ClientConnection) -> None:
            await ws.send(json.dumps({
                "method": "SUBSCRIBE",
                "params": list(streams),
                "id": 1,
            }))

        socket = ReconnectingWebSocket(self._url, tag="tokocrypto.ws.market",
                                       on_open=on_open, logger=self._logger)
        async for message in socket.messages():
            yield message
