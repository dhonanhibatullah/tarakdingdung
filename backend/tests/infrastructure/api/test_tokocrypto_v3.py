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
