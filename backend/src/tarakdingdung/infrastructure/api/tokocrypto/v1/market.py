import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v1.market import TokocryptoV1MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.transport import (
    BASE_URL,
    TokocryptoV1Transport,
)

# Type-1 (Binance-standard) market data / execution rules live on the `.site` host.
SITE_BASE_URL = "https://www.tokocrypto.site"


class HttpTokocryptoV1MarketApi(TokocryptoV1MarketApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "",
                 base_url: str = BASE_URL, site_base_url: str = SITE_BASE_URL) -> None:
        self._t = TokocryptoV1Transport(client, api_key=api_key, base_url=base_url)
        self._site = TokocryptoV1Transport(client, api_key=api_key, base_url=site_base_url)

    async def server_time(self) -> dict:
        # `/open/v1/common/time` carries the epoch in the top-level `timestamp`
        # field with a null `data`, so the envelope is returned unwrapped.
        return await self._t.public_get("/open/v1/common/time", raw=True)

    async def symbols(self) -> dict:
        return await self._t.public_get("/open/v1/common/symbols")

    async def depth(self, *, symbol: str, limit: int | None = None) -> dict:
        return await self._t.public_get("/open/v1/market/depth", symbol=symbol, limit=limit)

    async def trades(self, *, symbol: str, from_id: int | None = None,
                     limit: int | None = None) -> dict:
        return await self._t.public_get("/open/v1/market/trades", symbol=symbol,
                                        fromId=from_id, limit=limit)

    async def agg_trades(self, *, symbol: str, from_id: int | None = None,
                         start_time: int | None = None, end_time: int | None = None,
                         limit: int | None = None) -> dict:
        return await self._t.public_get("/open/v1/market/agg-trades", symbol=symbol,
                                        fromId=from_id, startTime=start_time,
                                        endTime=end_time, limit=limit)

    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> dict:
        return await self._t.public_get("/open/v1/market/klines", symbol=symbol,
                                        interval=interval, startTime=start_time,
                                        endTime=end_time, limit=limit)

    async def execution_rules(self, *, symbol: str | None = None, symbols: str | None = None,
                              symbol_status: str | None = None) -> dict:
        return await self._site.public_get("/api/v3/executionRules", raw=True, symbol=symbol,
                                           symbols=symbols, symbolStatus=symbol_status)
