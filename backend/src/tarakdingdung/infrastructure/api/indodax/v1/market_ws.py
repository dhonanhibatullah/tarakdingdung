import json
from collections.abc import AsyncIterator, Sequence
from itertools import count

import websockets

from tarakdingdung.domain.contracts.api.indodax.v1.market_ws import IndodaxMarketWebSocket
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.infrastructure.api.shared.websocket import ReconnectingWebSocket

_URL = "wss://ws3.indodax.com/ws/"
# Public static token from the Indodax Market Data WebSocket documentation.
_STATIC_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJleHAiOjE5NDY2MTg0MTV9"
    ".UR1lBM6Eqh0yWz-PVirw1uPCxe60FdchR8eNVdsskeo"
)
_SUBSCRIBE = 1
_PING = 7


class WsIndodaxMarketWebSocket(IndodaxMarketWebSocket):
    def __init__(self, *, url: str = _URL, static_token: str = _STATIC_TOKEN,
                 logger: LeveledLogger | None = None) -> None:
        self._url = url
        self._token = static_token
        self._logger = logger

    async def stream(self, channels: Sequence[str]) -> AsyncIterator[dict]:
        ids = count(1)

        async def on_open(ws: websockets.ClientConnection) -> None:
            await ws.send(json.dumps({"params": {"token": self._token}, "id": next(ids)}))
            for channel in channels:
                await ws.send(json.dumps({
                    "method": _SUBSCRIBE,
                    "params": {"channel": channel},
                    "id": next(ids),
                }))

        async def ping(ws: websockets.ClientConnection) -> None:
            await ws.send(json.dumps({"method": _PING, "id": next(ids)}))

        socket = ReconnectingWebSocket(self._url, tag="indodax.ws.market", on_open=on_open,
                                       ping=ping, logger=self._logger)
        async for message in socket.messages():
            yield message
