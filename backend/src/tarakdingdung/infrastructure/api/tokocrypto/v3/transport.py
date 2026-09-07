import time
from collections.abc import Callable
from typing import Any

import httpx

from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256
from tarakdingdung.infrastructure.api.tokocrypto.v3.errors import map_v3_error

V3_BASE_URL = "https://www.tokocrypto.site"


def default_now_ms() -> int:
    return int(time.time() * 1000)


class TokocryptoV3Transport:
    """Binance-standard `/api/v3/*` plumbing on the `.site` host.

    Responses are raw JSON — there is no `{code,msg,data}` envelope to unwrap.
    Failures arrive as a `{"code","msg"}` body with a 4xx status, so the
    RestClient is handed `map_v3_error` to read that body. Signed calls put the
    whole signed parameter string in the query for every verb; Binance accepts
    POST and DELETE parameters there.
    """

    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "",
                 secret_key: str = "", base_url: str = V3_BASE_URL,
                 recv_window: int | None = None,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="tokocrypto.v3",
                                error_mapper=map_v3_error)
        self._api_key = api_key
        self._secret_key = secret_key
        self._recv_window = recv_window
        self._now_ms = now_ms

    def _key_header(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self._api_key} if self._api_key else {}

    async def public_get(self, path: str, **params: Any) -> Any:
        return await self._rest.request(
            "GET", path, query=encode_params(params) or None,
            headers=self._key_header())

    async def signed_request(self, method: str, path: str, **params: Any) -> Any:
        base: dict[str, Any] = {"timestamp": self._now_ms()}
        if self._recv_window is not None:
            base["recvWindow"] = self._recv_window
        encoded = encode_params({**base, **params})
        signed = f"{encoded}&signature={hmac_sha256(self._secret_key, encoded)}"
        return await self._rest.request(method, path, query=signed,
                                       headers=self._key_header())
