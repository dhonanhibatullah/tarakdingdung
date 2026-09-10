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
            json={
                "s": "ok",
                "t": [1000, 1060],
                "o": ["1", "2"],
                "h": ["3", "4"],
                "l": ["0.5", "1.5"],
                "c": ["2", "3"],
                "v": ["10", "20"],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    candles = await api.fetch_candles(_symbol(), "60", 1_000_000, 2_000_000)

    assert len(candles) == 2
    assert candles[0].symbol_id == "s1"
    assert candles[0].open == Decimal("1")
    assert candles[0].open_time_ms == 1_000_000
    assert candles[1].close == Decimal("3")


async def test_fetch_candles_requests_tradingview_symbol():
    captured = {}

    def handler(request):
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"t": [], "o": [], "h": [], "l": [], "c": [], "v": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    await api.fetch_candles(_symbol(), "60", 1_000_000, 2_000_000)

    assert captured["params"]["symbol"] == "BTCIDR"
    assert captured["params"]["tf"] == "60"


async def test_fetch_ticker():
    def handler(request):
        return httpx.Response(
            200,
            json={"ticker": {"last": "98765", "server_time": 1700000000000}},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpIndodaxPublicApi(client)
    ticker = await api.fetch_ticker(_symbol())

    assert ticker.symbol_id == "s1"
    assert ticker.last_price == Decimal("98765")
    assert ticker.timestamp_ms == 1700000000000
