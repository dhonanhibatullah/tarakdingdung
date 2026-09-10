import hashlib
import hmac
import time
from decimal import Decimal
from urllib.parse import urlencode

import httpx

from tarakdingdung.domain.contracts.trade.exchange import (
    Account,
    AccountBalance,
    Exchange,
    OrderResult,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.order import OrderSide
from tarakdingdung.domain.models.symbol import Symbol


class HttpIndodaxV2Api(Exchange):
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        secret: str,
        base_url: str = "https://api.indodax.com",
        now_ms: callable = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._secret = secret
        self._base_url = base_url.rstrip("/")
        self._now = now_ms or (lambda: int(time.time() * 1000))

    def _sign(self, message: str) -> str:
        return hmac.new(
            self._secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _headers(self, message: str) -> dict:
        return {"X-APIKEY": self._api_key, "Sign": self._sign(message)}

    def _raise_for_error(self, data: dict, *, not_found: bool = False) -> None:
        code = data.get("code")
        if isinstance(code, int) and code < 0:
            error_type = ErrorType.NOT_FOUND if not_found else ErrorType.INTERNAL
            raise DomainError(data.get("msg", "exchange error"), error_type)

    async def account(self) -> Account:
        params = f"timestamp={self._now()}&recvWindow=5000"
        resp = await self._client.get(
            f"{self._base_url}/api/v2/account?{params}", headers=self._headers(params)
        )
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_error(data)
        balances = [
            AccountBalance(
                asset=b["asset"],
                free=Decimal(str(b["free"])),
                locked=Decimal(str(b["locked"])),
            )
            for b in data.get("balances", [])
        ]
        return Account(balances=balances)

    async def place_order(
        self,
        symbol: Symbol,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        client_order_id: str,
    ) -> OrderResult:
        params = {
            "symbol": symbol.external,
            "side": "BUY" if side is OrderSide.BUY else "SELL",
            "type": "LIMIT",
            "quantity": str(quantity),
            "price": str(price),
            "newClientOrderId": client_order_id,
            "timestamp": str(self._now()),
            "recvWindow": "5000",
        }
        body = urlencode(params)
        resp = await self._client.post(
            f"{self._base_url}/api/v2/order",
            content=body,
            headers={
                **self._headers(body),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_error(data)
        return OrderResult(
            order_id=str(data.get("orderId", "")),
            client_order_id=client_order_id,
            status=str(data.get("status", "")),
            filled_quantity=Decimal(str(data.get("executedQty") or "0")),
        )

    async def get_order(self, symbol: Symbol, order_id: str) -> OrderResult:
        params = (
            f"symbol={symbol.external}&orderId={order_id}"
            f"&timestamp={self._now()}&recvWindow=5000"
        )
        resp = await self._client.get(
            f"{self._base_url}/api/v2/order?{params}", headers=self._headers(params)
        )
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_error(data, not_found=True)
        return OrderResult(
            order_id=str(data.get("orderId", order_id)),
            client_order_id=str(data.get("newClientOrderId", order_id)),
            status=str(data.get("status", "")),
            filled_quantity=Decimal(str(data.get("executedQty") or "0")),
        )

    async def cancel_order(self, symbol: Symbol, order_id: str) -> None:
        params = f"symbol={symbol.external}&orderId={order_id}&timestamp={self._now()}&recvWindow=5000"
        resp = await self._client.request(
            "DELETE",
            f"{self._base_url}/api/v2/order?{params}",
            headers=self._headers(params),
        )
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_error(data)
