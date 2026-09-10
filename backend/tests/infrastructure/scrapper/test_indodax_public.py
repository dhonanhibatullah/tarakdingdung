from decimal import Decimal

import httpx

from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.infrastructure.scrapper.indodax.public import HttpIndodaxPublicApi


def _symbol():
    return Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")


async def test_fetch_candles():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "Time": 1000,
                    "Open": 1371027000,
                    "High": 1374765000,
                    "Low": 1368572000,
                    "Close": 1374765000,
                    "Volume": "0.54342495",
                },
                {
                    "Time": 1060,
                    "Open": 1374765000,
                    "High": 1379726000,
                    "Low": 1374764000,
                    "Close": 1377031000,
                    "Volume": "0.36980219",
                },
            ],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    candles = await api.fetch_candles(_symbol(), "60", 1_000_000, 2_000_000)

    assert len(candles) == 2
    assert candles[0].symbol_id == "s1"
    assert candles[0].open_time_ms == 1_000_000
    assert candles[0].open == Decimal("1371027000")
    assert candles[0].volume == Decimal("0.54342495")
    assert candles[1].close == Decimal("1377031000")


async def test_fetch_candles_requests_tradingview_symbol():
    captured = {}

    def handler(request):
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    await api.fetch_candles(_symbol(), "60", 1_000_000, 2_000_000)

    assert captured["params"]["symbol"] == "BTCIDR"
    assert captured["params"]["tf"] == "60"


async def test_fetch_ticker():
    def handler(request):
        return httpx.Response(
            200,
            json={"ticker": {"last": "1379323000", "server_time": 1789015293}},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    ticker = await api.fetch_ticker(_symbol())

    assert ticker.symbol_id == "s1"
    assert ticker.last_price == Decimal("1379323000")
    assert ticker.timestamp_ms == 1789015293000
