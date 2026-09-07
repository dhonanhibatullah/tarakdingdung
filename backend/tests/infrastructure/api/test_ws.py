import json

import httpx
import pytest

from tarakdingdung.infrastructure.api.shared import websocket as ws_mod
from tarakdingdung.infrastructure.api.indodax.v1.market_ws import WsIndodaxMarketWebSocket
from tarakdingdung.infrastructure.api.tokocrypto.v1.market import HttpTokocryptoV1MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.market_ws import (
    WsTokocryptoMarketWebSocket,
)
from tarakdingdung.infrastructure.api.tokocrypto.v1.user_ws import WsTokocryptoUserWebSocket


class _FakeWS:
    def __init__(self, url: str, incoming: list) -> None:
        self.url = url
        self.sent: list[str] = []
        self._incoming = list(incoming)

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def __aenter__(self) -> "_FakeWS":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    def __aiter__(self) -> "_FakeWS":
        return self

    async def __anext__(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        raise StopAsyncIteration


@pytest.fixture
def fake_connect(monkeypatch):
    created: list[_FakeWS] = []
    canned = [json.dumps({"hello": 1}), json.dumps({"hello": 2})]

    def _connect(url: str, **_kwargs: object) -> _FakeWS:
        ws = _FakeWS(url, canned)
        created.append(ws)
        return ws

    monkeypatch.setattr(ws_mod.websockets, "connect", _connect)
    return created


async def _drain(gen, n: int) -> list:
    out = []
    async for msg in gen:
        out.append(msg)
        if len(out) >= n:
            break
    await gen.aclose()
    return out


@pytest.mark.asyncio
async def test_indodax_market_ws_sends_auth_then_subscribe(fake_connect):
    api = WsIndodaxMarketWebSocket(static_token="tok-123")
    got = await _drain(api.stream(["chart:tick-btcidr", "market:summary-24h"]), 2)

    assert got == [{"hello": 1}, {"hello": 2}]
    frames = [json.loads(f) for f in fake_connect[0].sent]
    assert frames[0] == {"params": {"token": "tok-123"}, "id": 1}
    assert frames[1] == {"method": 1, "params": {"channel": "chart:tick-btcidr"}, "id": 2}
    assert frames[2] == {"method": 1, "params": {"channel": "market:summary-24h"}, "id": 3}


@pytest.mark.asyncio
async def test_tokocrypto_market_ws_sends_subscribe_frame(fake_connect):
    api = WsTokocryptoMarketWebSocket()
    await _drain(api.stream(["btcusdt@aggTrade", "btcusdt@kline_1m"]), 2)

    assert json.loads(fake_connect[0].sent[0]) == {
        "method": "SUBSCRIBE",
        "params": ["btcusdt@aggTrade", "btcusdt@kline_1m"],
        "id": 1,
    }
    assert fake_connect[0].url == "wss://stream-cloud.tokocrypto.site/stream"


@pytest.mark.asyncio
async def test_tokocrypto_user_ws_builds_stream_url_from_listen_token(fake_connect):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "msg": "", "data": {"listenToken": "LK9"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = WsTokocryptoUserWebSocket(client, api_key="k", secret_key="s")
    await _drain(api.stream(), 1)

    assert fake_connect[0].url == "wss://stream-cloud.tokocrypto.site/stream?streams=LK9"


@pytest.mark.asyncio
async def test_tokocrypto_execution_rules_uses_site_host():
    seen: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        return httpx.Response(200, json=[{"symbol": "BTC_USDT"}])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = HttpTokocryptoV1MarketApi(client)
    out = await api.execution_rules(symbol="BTC_USDT")

    assert out == [{"symbol": "BTC_USDT"}]
    assert seen["url"].host == "www.tokocrypto.site"
    assert seen["url"].path == "/api/v3/executionRules"
