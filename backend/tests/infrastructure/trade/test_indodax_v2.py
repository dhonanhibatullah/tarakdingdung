from decimal import Decimal

import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.order import OrderSide
from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.infrastructure.trade.indodax.v2 import HttpIndodaxV2Api


def _symbol():
    return Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")


def _api(handler, now=1000):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HttpIndodaxV2Api(client, api_key="key", secret="secret", now_ms=lambda: now)


async def test_account_parses_balances():
    def handler(request):
        assert request.headers["x-apikey"] == "key"
        assert "Sign" in request.headers
        return httpx.Response(
            200,
            json={"balances": [{"asset": "idr", "free": "1000", "locked": "5"}]},
        )

    api = _api(handler)
    account = await api.account()
    assert account.balances[0].asset == "idr"
    assert account.balances[0].free == Decimal("1000")
    assert account.balances[0].locked == Decimal("5")


async def test_place_order_posts_body_and_signs():
    captured = {}

    def handler(request):
        captured["method"] = request.method
        captured["content"] = request.content.decode()
        captured["sign"] = request.headers.get("sign")
        return httpx.Response(200, json={"orderId": "123", "status": "NEW"})

    api = _api(handler)
    result = await api.place_order(
        _symbol(), OrderSide.BUY, Decimal("0.5"), Decimal("100"), "client-1"
    )
    assert result.order_id == "123"
    assert captured["method"] == "POST"
    assert "newClientOrderId=client-1" in captured["content"]
    assert "side=BUY" in captured["content"]
    assert captured["sign"]


async def test_get_order_not_found_raises():
    def handler(request):
        return httpx.Response(200, json={"code": -2013, "msg": "Order does not exist."})

    api = _api(handler)
    with pytest.raises(DomainError) as exc:
        await api.get_order(_symbol(), "client-1")
    assert exc.value.error_type.value == "not_found"
