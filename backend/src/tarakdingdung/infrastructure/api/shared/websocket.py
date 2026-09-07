import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable

import websockets
from websockets.exceptions import WebSocketException

from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger

UrlSource = str | Callable[[], Awaitable[str]]
OnOpen = Callable[[websockets.ClientConnection], Awaitable[None]]
Ping = Callable[[websockets.ClientConnection], Awaitable[None]]


class ReconnectingWebSocket:
    """A JSON WebSocket consumer that reconnects with capped exponential
    backoff and re-runs its ``on_open`` handshake (auth + subscribe) on every
    (re)connection.

    - ``url`` may be a string or an async factory (used when the URL embeds a
      short-lived token that must be refreshed per connection).
    - ``on_open`` sends the auth/subscribe frames.
    - ``ping`` (optional) sends an application-level keep-alive; it is called
      every ``ping_interval`` seconds while connected. Protocol-level ping/pong
      is handled by the library via ``ping_interval``/``ping_timeout``.
    """

    def __init__(self, url: UrlSource, *, tag: str, on_open: OnOpen | None = None,
                 ping: Ping | None = None, ping_interval: float = 25.0,
                 max_backoff: float = 30.0,
                 logger: LeveledLogger | None = None) -> None:
        self._url = url
        self._tag = tag
        self._on_open = on_open
        self._ping = ping
        self._ping_interval = ping_interval
        self._max_backoff = max_backoff
        self._log = logger

    async def messages(self) -> AsyncIterator[dict]:
        backoff = 1.0
        while True:
            try:
                url = self._url if isinstance(self._url, str) else await self._url()
                async with websockets.connect(url, ping_interval=20,
                                              ping_timeout=20) as ws:
                    backoff = 1.0
                    if self._on_open is not None:
                        await self._on_open(ws)
                    ping_task = (
                        asyncio.create_task(self._ping_loop(ws))
                        if self._ping is not None else None
                    )
                    try:
                        async for raw in ws:
                            try:
                                yield json.loads(raw)
                            except (ValueError, TypeError):
                                continue
                    finally:
                        if ping_task is not None:
                            ping_task.cancel()
            except asyncio.CancelledError:
                raise
            except (WebSocketException, OSError, asyncio.TimeoutError) as exc:
                await self._warn(f"disconnected, retrying in {backoff:.0f}s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff)

    async def _ping_loop(self, ws: websockets.ClientConnection) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                await self._ping(ws)  # type: ignore[misc]
        except (asyncio.CancelledError, WebSocketException, OSError):
            return

    async def _warn(self, message: str, exc: Exception) -> None:
        if self._log is not None:
            await self._log.warn(self._tag, message, {"error": str(exc)})
