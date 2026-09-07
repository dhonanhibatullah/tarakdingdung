"""Tokocrypto v3 market API client."""
import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v3.market import TokocryptoV3MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import (
    V3_BASE_URL,
    TokocryptoV3Transport,
)


class HttpTokocryptoV3MarketApi(TokocryptoV3MarketApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "",
                 base_url: str = V3_BASE_URL) -> None:
        self._t = TokocryptoV3Transport(client, api_key=api_key, base_url=base_url)

    async def server_time(self) -> dict:
        return await self._t.public_get("/api/v3/time")

    async def exchange_info(self, *, symbol: str | None = None,
                            symbols: str | None = None) -> dict:
        return await self._t.public_get("/api/v3/exchangeInfo", symbol=symbol,
                                        symbols=symbols)

    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> list:
        return await self._t.public_get("/api/v3/klines", symbol=symbol,
                                        interval=interval, startTime=start_time,
                                        endTime=end_time, limit=limit)

    async def depth(self, *, symbol: str, limit: int | None = None) -> dict:
        return await self._t.public_get("/api/v3/depth", symbol=symbol, limit=limit)

    async def ticker_price(self, *, symbol: str) -> dict:
        return await self._t.public_get("/api/v3/ticker/price", symbol=symbol)
