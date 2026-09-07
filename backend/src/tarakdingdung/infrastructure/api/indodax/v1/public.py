import httpx

from tarakdingdung.domain.contracts.api.indodax.v1.public import IndodaxV1PublicApi
from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params

_BASE_URL = "https://indodax.com"


class HttpIndodaxV1PublicApi(IndodaxV1PublicApi):
    def __init__(self, client: httpx.AsyncClient, *, base_url: str = _BASE_URL) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="indodax.v1.public")

    async def server_time(self) -> dict:
        return await self._rest.request("GET", "/api/server_time")

    async def pairs(self) -> list:
        return await self._rest.request("GET", "/api/pairs")

    async def price_increments(self) -> dict:
        return await self._rest.request("GET", "/api/price_increments")

    async def summaries(self) -> dict:
        return await self._rest.request("GET", "/api/summaries")

    async def ticker(self, pair_id: str = "btcidr") -> dict:
        return await self._rest.request("GET", f"/api/ticker/{pair_id}")

    async def ticker_all(self) -> dict:
        return await self._rest.request("GET", "/api/ticker_all")

    async def trades(self, pair_id: str = "btcidr") -> list:
        return await self._rest.request("GET", f"/api/trades/{pair_id}")

    async def depth(self, pair_id: str = "btcidr") -> dict:
        return await self._rest.request("GET", f"/api/depth/{pair_id}")

    async def ohlc(self, *, symbol: str, tf: str, from_ts: int, to_ts: int) -> list:
        query = encode_params({"symbol": symbol, "tf": tf, "from": from_ts, "to": to_ts})
        return await self._rest.request("GET", "/tradingview/history_v2", query=query)
