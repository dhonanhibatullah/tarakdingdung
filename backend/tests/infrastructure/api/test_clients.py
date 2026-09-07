import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.indodax.v1.private import HttpIndodaxV1PrivateApi
from tarakdingdung.infrastructure.api.indodax.v1.public import HttpIndodaxV1PublicApi
from tarakdingdung.infrastructure.api.indodax.v2.trade import HttpIndodaxV2TradeApi
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256, hmac_sha512
from tarakdingdung.infrastructure.api.tokocrypto.v1.market import HttpTokocryptoV1MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.trade import HttpTokocryptoV1TradeApi

_FIXED_NOW = lambda: 1_700_000_000_000


class _Capture:
    request: httpx.Request | None = None

    def client(self, response: httpx.Response) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            self.request = request
            return response

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_indodax_v1_public_hits_plain_get():
    cap = _Capture()
    api = HttpIndodaxV1PublicApi(cap.client(httpx.Response(200, json={"server_time": 1})))
    assert await api.server_time() == {"server_time": 1}
    assert cap.request.method == "GET"
    assert str(cap.request.url) == "https://indodax.com/api/server_time"


@pytest.mark.asyncio
async def test_indodax_v1_private_signs_body_and_unwraps_return():
    cap = _Capture()
    body = {"success": 1, "return": {"balance": {"idr": 0}}}
    api = HttpIndodaxV1PrivateApi(cap.client(httpx.Response(200, json=body)),
                                  api_key="the-key", secret_key="the-secret",
                                  now_ms=_FIXED_NOW)
    assert await api.get_info() == {"balance": {"idr": 0}}

    sent = cap.request.content.decode()
    assert sent == "method=getInfo&timestamp=1700000000000&recvWindow=5000"
    assert cap.request.headers["Key"] == "the-key"
    assert cap.request.headers["Sign"] == hmac_sha512("the-secret", sent)


@pytest.mark.asyncio
async def test_indodax_v1_private_raises_on_success_zero():
    cap = _Capture()
    body = {"success": 0, "error": "Invalid credentials.", "error_code": "invalid_credentials"}
    api = HttpIndodaxV1PrivateApi(cap.client(httpx.Response(200, json=body)),
                                  api_key="k", secret_key="s")
    with pytest.raises(DomainError) as ei:
        await api.get_info()
    assert ei.value.type is ErrorType.UNAUTHORIZED


@pytest.mark.asyncio
async def test_indodax_v2_signs_query_and_raises_on_negative_code():
    cap = _Capture()
    api = HttpIndodaxV2TradeApi(
        cap.client(httpx.Response(200, json={"code": -2015, "msg": "Access denied."})),
        api_key="ak", secret_key="sk", now_ms=_FIXED_NOW)
    with pytest.raises(DomainError) as ei:
        await api.account()
    assert ei.value.type is ErrorType.FORBIDDEN

    qs = "timestamp=1700000000000&recvWindow=5000"
    assert cap.request.url.query.decode() == qs
    assert cap.request.headers["X-APIKEY"] == "ak"
    assert cap.request.headers["Sign"] == hmac_sha256("sk", qs)


@pytest.mark.asyncio
async def test_indodax_v2_account_ok_returns_body():
    cap = _Capture()
    body = {"canTrade": True, "canWithdraw": False, "balances": []}
    api = HttpIndodaxV2TradeApi(cap.client(httpx.Response(200, json=body)),
                                api_key="ak", secret_key="sk")
    assert await api.account() == body


@pytest.mark.asyncio
async def test_tokocrypto_market_unwraps_data_envelope():
    cap = _Capture()
    api = HttpTokocryptoV1MarketApi(
        cap.client(httpx.Response(200, json={"code": 0, "msg": "", "data": {"bids": []}})))
    assert await api.depth(symbol="BTCIDR") == {"bids": []}
    assert cap.request.url.path == "/open/v1/market/depth"
    assert cap.request.url.params["symbol"] == "BTCIDR"


@pytest.mark.asyncio
async def test_tokocrypto_server_time_returns_raw_envelope():
    cap = _Capture()
    body = {"code": 0, "msg": "Success", "data": None, "timestamp": 1788755504064}
    api = HttpTokocryptoV1MarketApi(cap.client(httpx.Response(200, json=body)))
    assert await api.server_time() == body


@pytest.mark.asyncio
async def test_tokocrypto_signed_appends_signature_and_unwraps():
    cap = _Capture()
    api = HttpTokocryptoV1TradeApi(
        cap.client(httpx.Response(200, json={"code": 0, "msg": "", "data": {"accountAssets": []}})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    assert await api.account() == {"accountAssets": []}

    query = cap.request.url.query.decode()
    assert query.startswith("timestamp=1700000000000&recvWindow=5000&signature=")
    unsigned = "timestamp=1700000000000&recvWindow=5000"
    assert query == f"{unsigned}&signature={hmac_sha256('sec', unsigned)}"
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"


@pytest.mark.asyncio
async def test_tokocrypto_signed_raises_on_non_zero_code():
    cap = _Capture()
    api = HttpTokocryptoV1TradeApi(
        cap.client(httpx.Response(200, json={"code": -1003, "msg": "Too many requests"})),
        api_key="mbx", secret_key="sec")
    with pytest.raises(DomainError) as ei:
        await api.account()
    assert ei.value.type is ErrorType.RATE_LIMITED
