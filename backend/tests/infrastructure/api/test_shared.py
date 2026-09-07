import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.shared.rest import RestClient, clean_params, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256, hmac_sha512


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_signing_matches_known_vectors():
    assert hmac_sha256("secret", "payload") == (
        "b82fcb791acec57859b989b430a826488ce2e479fdf92326bd0a2e8375a42ba4"
    )
    # From the Indodax Trade API v1 docs' worked example.
    body = "method=getInfo&timestamp=1578304294000&recvWindow=1578303937000"
    secret = "f60617a68fcce028f0a90bc9eb765d17379eb548cc935c01a7ee3186eecf870e9b68f27a31bcfe8d"
    assert hmac_sha512(secret, body) == (
        "bab004e5a518740d7a33b38b44dbebecd3fb39f40b42391af39fcce06edabff52"
        "33b3e8064a07c528d1c751a6923d5116026c7786e01b22e2d35277a098cae99"
    )


def test_clean_params_drops_none_and_stringifies_bools():
    assert clean_params({"a": 1, "b": None, "c": True, "d": False}) == {
        "a": 1, "c": "true", "d": "false",
    }


def test_encode_params_is_stable_urlencoding():
    assert encode_params({"b": 2, "a": 1, "skip": None}) == "b=2&a=1"


@pytest.mark.asyncio
async def test_rest_client_maps_429_to_rate_limited():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down")

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t")
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.RATE_LIMITED


@pytest.mark.asyncio
async def test_rest_client_maps_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom", request=request)

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t")
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.TIMEOUT


@pytest.mark.asyncio
async def test_rest_client_returns_decoded_json():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": 1})

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t")
    assert await rest.request("GET", "/ping") == {"ok": 1}


@pytest.mark.asyncio
async def test_rest_client_uses_the_error_mapper_when_given_one():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, text='{"code":-1121,"msg":"Invalid symbol."}')

    def mapper(status: int, body: str) -> DomainError:
        assert status == 418 and "Invalid symbol." in body
        return DomainError("mapped it", ErrorType.BAD_ARGS)

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t",
                      error_mapper=mapper)
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.BAD_ARGS
    assert ei.value.message == "mapped it"


@pytest.mark.asyncio
async def test_rest_client_without_a_mapper_is_unchanged():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="plain")

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t")
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.BAD_ARGS  # from _STATUS_ERROR[400]
