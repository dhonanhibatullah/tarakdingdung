import json
from collections.abc import AsyncIterator

import httpx
import websockets

from tarakdingdung.domain.contracts.api.indodax.v1.private_ws import IndodaxPrivateWebSocket
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.indodax.errors import raise_v1_error
from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha512
from tarakdingdung.infrastructure.api.shared.websocket import ReconnectingWebSocket

_TOKEN_BASE_URL = "https://indodax.com"
_TOKEN_PATH = "/api/private_ws/v1/generate_token"
_WS_URL = "wss://pws.indodax.com/ws/?cf_ws_frame_ping_pong=true"


class WsIndodaxPrivateWebSocket(IndodaxPrivateWebSocket):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 token_base_url: str = _TOKEN_BASE_URL, ws_url: str = _WS_URL,
                 logger: LeveledLogger | None = None) -> None:
        self._rest = RestClient(client, base_url=token_base_url, tag="indodax.ws.private")
        self._api_key = api_key
        self._secret_key = secret_key
        self._ws_url = ws_url
        self._logger = logger

    async def _generate_token(self) -> tuple[str, str]:
        body = encode_params({"client": "tapi", "tapi_key": self._api_key})
        headers = {
            "Sign": hmac_sha512(self._secret_key, body),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = await self._rest.request("POST", _TOKEN_PATH, body=body, headers=headers)
        raise_v1_error(payload)
        data = payload.get("return", {}) if isinstance(payload, dict) else {}
        conn_token, channel = data.get("connToken"), data.get("channel")
        if not conn_token or not channel:
            raise DomainError("indodax.ws.private: token response missing connToken/channel",
                              ErrorType.UPSTREAM)
        return conn_token, channel

    async def stream(self) -> AsyncIterator[dict]:
        async def on_open(ws: websockets.ClientConnection) -> None:
            conn_token, channel = await self._generate_token()
            await ws.send(json.dumps({"connect": {"token": conn_token}, "id": 1}))
            await ws.send(json.dumps({"subscribe": {"channel": channel}, "id": 2}))

        socket = ReconnectingWebSocket(self._ws_url, tag="indodax.ws.private",
                                       on_open=on_open, logger=self._logger)
        async for message in socket.messages():
            yield message
