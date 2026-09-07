import time
from collections.abc import Callable
from typing import Any

import httpx

from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256
from tarakdingdung.infrastructure.api.tokocrypto.errors import unwrap

BASE_URL = "https://www.tokocrypto.com"


def default_now_ms() -> int:
    return int(time.time() * 1000)


class TokocryptoV1Transport:
    """Shared request/sign/unwrap plumbing for the Tokocrypto `/open/v1/*`
    endpoints. Public calls send only the ``X-MBX-APIKEY`` header (when a key is
    configured); signed calls append ``&signature=<HMAC-SHA256>`` to the param
    string. Every call is unwrapped from the ``{code,msg,data}`` envelope.
    """

    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "", secret_key: str = "",
                 base_url: str = BASE_URL, recv_window: int | None = None,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="tokocrypto.v1")
        self._api_key = api_key
        self._secret_key = secret_key
        self._recv_window = recv_window
        self._now_ms = now_ms

    def _key_header(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self._api_key} if self._api_key else {}

    async def public_get(self, path: str, *, raw: bool = False, **params: Any) -> Any:
        query = encode_params(params)
        payload = await self._rest.request("GET", path, query=query or None,
                                           headers=self._key_header())
        return payload if raw else unwrap(payload)

    async def signed_get(self, path: str, **params: Any) -> Any:
        return await self._signed("GET", path, params)

    async def signed_post(self, path: str, **params: Any) -> Any:
        return await self._signed("POST", path, params)

    async def _signed(self, http_method: str, path: str, params: dict[str, Any]) -> Any:
        base = {"timestamp": self._now_ms()}
        if self._recv_window is not None:
            base["recvWindow"] = self._recv_window
        encoded = encode_params({**base, **params})
        signed = f"{encoded}&signature={hmac_sha256(self._secret_key, encoded)}"
        headers = self._key_header()
        if http_method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = await self._rest.request("POST", path, body=signed, headers=headers)
        else:
            payload = await self._rest.request("GET", path, query=signed, headers=headers)
        return unwrap(payload)
