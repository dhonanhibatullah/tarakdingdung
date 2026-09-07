import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.tokocrypto.v3.errors import map_v3_error
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import TokocryptoV3Transport


def test_map_v3_error_reads_the_binance_code():
    err = map_v3_error(400, '{"code":-1121,"msg":"Invalid symbol."}')
    assert err.type is ErrorType.BAD_ARGS
    assert "Invalid symbol." in err.message


def test_map_v3_error_maps_a_state_code():
    err = map_v3_error(400, '{"code":-2010,"msg":"Account has insufficient balance."}')
    assert err.type is ErrorType.BAD_STATE


def test_map_v3_error_falls_back_to_status_when_body_is_opaque():
    assert map_v3_error(401, "not json").type is ErrorType.UNAUTHORIZED
    assert map_v3_error(500, "boom").type is ErrorType.UPSTREAM


def test_map_v3_error_unknown_code_is_upstream():
    assert map_v3_error(400, '{"code":-9999,"msg":"nope"}').type is ErrorType.UPSTREAM


_FIXED_NOW = lambda: 1_700_000_000_000


class _Capture:
    request: httpx.Request | None = None

    def client(self, response: httpx.Response) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            self.request = request
            return response
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_v3_public_get_sends_key_header_and_returns_raw_json():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json={"serverTime": 1})),
                              api_key="mbx")
    assert await t.public_get("/api/v3/time") == {"serverTime": 1}
    assert cap.request.method == "GET"
    assert cap.request.url.path == "/api/v3/time"
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"


async def test_v3_public_get_omits_none_params_and_the_header_without_a_key():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json=[])))
    await t.public_get("/api/v3/klines", symbol="BTCIDR", interval="1h", limit=None)
    assert cap.request.url.query.decode() == "symbol=BTCIDR&interval=1h"
    assert "X-MBX-APIKEY" not in cap.request.headers


async def test_v3_signed_request_appends_the_signature_over_the_encoded_query():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json={"ok": 1})),
                              api_key="mbx", secret_key="sec", recv_window=5000,
                              now_ms=_FIXED_NOW)
    await t.signed_request("POST", "/api/v3/order", symbol="BTCIDR", side="BUY")
    unsigned = "timestamp=1700000000000&recvWindow=5000&symbol=BTCIDR&side=BUY"
    assert cap.request.url.query.decode() == (
        f"{unsigned}&signature={hmac_sha256('sec', unsigned)}")
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"


async def test_v3_transport_maps_a_binance_error_body():
    cap = _Capture()
    t = TokocryptoV3Transport(
        cap.client(httpx.Response(400, text='{"code":-1121,"msg":"Invalid symbol."}')))
    with pytest.raises(DomainError) as ei:
        await t.public_get("/api/v3/depth", symbol="NOPE")
    assert ei.value.type is ErrorType.BAD_ARGS


from tarakdingdung.infrastructure.api.tokocrypto.v3.market import HttpTokocryptoV3MarketApi


async def test_v3_market_klines_passes_params_and_returns_the_array():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(
        cap.client(httpx.Response(200, json=[[1, "1", "2", "0.5", "1.5", "10"]])))
    rows = await api.klines(symbol="BTCIDR", interval="1h", limit=2)
    assert rows == [[1, "1", "2", "0.5", "1.5", "10"]]
    assert cap.request.url.path == "/api/v3/klines"
    assert cap.request.url.params["symbol"] == "BTCIDR"
    assert cap.request.url.params["interval"] == "1h"
    assert cap.request.url.params["limit"] == "2"


async def test_v3_market_ticker_price_returns_the_object():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(
        cap.client(httpx.Response(200, json={"symbol": "BTCIDR", "price": "1397.00"})))
    assert await api.ticker_price(symbol="BTCIDR") == {"symbol": "BTCIDR", "price": "1397.00"}
    assert cap.request.url.path == "/api/v3/ticker/price"


async def test_v3_market_depth_and_exchange_info_hit_their_paths():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(cap.client(httpx.Response(200, json={"bids": [], "asks": []})))
    await api.depth(symbol="BTCIDR", limit=5)
    assert cap.request.url.path == "/api/v3/depth"
    api2 = HttpTokocryptoV3MarketApi(cap.client(httpx.Response(200, json={"symbols": []})))
    await api2.exchange_info()
    assert cap.request.url.path == "/api/v3/exchangeInfo"


from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import HttpTokocryptoV3TradeApi


async def test_v3_trade_create_order_maps_snake_to_camel_and_defaults_full_resp():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"orderId": 7, "fills": []})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    out = await api.create_order(symbol="BTCIDR", side="BUY", type="LIMIT",
                                 quantity="1", price="1000",
                                 time_in_force="GTC", new_client_order_id="tdd1")
    assert out == {"orderId": 7, "fills": []}
    q = cap.request.url.query.decode()
    assert cap.request.method == "POST"
    assert cap.request.url.path == "/api/v3/order"
    assert "symbol=BTCIDR" in q and "side=BUY" in q and "type=LIMIT" in q
    assert "newClientOrderId=tdd1" in q and "newOrderRespType=FULL" in q
    assert "timeInForce=GTC" in q
    assert "&signature=" in q


async def test_v3_trade_account_is_signed():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"balances": []})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    assert await api.account() == {"balances": []}
    assert cap.request.url.path == "/api/v3/account"
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"
    assert "&signature=" in cap.request.url.query.decode()


async def test_v3_trade_query_order_uses_orig_client_order_id():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"status": "FILLED"})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    await api.query_order(symbol="BTCIDR", orig_client_order_id="tdd1")
    assert cap.request.method == "GET"
    assert "origClientOrderId=tdd1" in cap.request.url.query.decode()
