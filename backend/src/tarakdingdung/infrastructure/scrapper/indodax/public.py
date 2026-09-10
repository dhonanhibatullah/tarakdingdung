from decimal import Decimal

import httpx

from tarakdingdung.domain.contracts.scrapper.market_source import MarketSource
from tarakdingdung.domain.models.market import Candle, Ticker
from tarakdingdung.domain.models.symbol import Symbol


class HttpIndodaxPublicApi(MarketSource):
    def __init__(
        self, client: httpx.AsyncClient, base_url: str = "https://indodax.com"
    ) -> None:
        self._client = client
        self._base_url = base_url

    async def fetch_candles(
        self, symbol: Symbol, interval: str, from_ms: int, to_ms: int
    ) -> list[Candle]:
        resp = await self._client.get(
            f"{self._base_url}/tradingview/history_v2",
            params={
                "symbol": symbol.external,
                "from": from_ms // 1000,
                "to": to_ms // 1000,
                "tf": interval,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        times = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        candles: list[Candle] = []
        for i in range(len(times)):
            candles.append(
                Candle(
                    symbol_id=symbol.id,
                    open_time_ms=times[i] * 1000,
                    open=Decimal(str(opens[i])),
                    high=Decimal(str(highs[i])),
                    low=Decimal(str(lows[i])),
                    close=Decimal(str(closes[i])),
                    volume=Decimal(str(volumes[i])),
                )
            )
        return candles

    async def fetch_ticker(self, symbol: Symbol) -> Ticker:
        resp = await self._client.get(
            f"{self._base_url}/api/ticker/{symbol.external.lower()}"
        )
        resp.raise_for_status()
        data = resp.json()
        ticker = data["ticker"]
        return Ticker(
            symbol_id=symbol.id,
            last_price=Decimal(str(ticker["last"])),
            timestamp_ms=int(ticker["server_time"]),
        )
