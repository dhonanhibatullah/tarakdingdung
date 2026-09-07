"""Tokocrypto v3 trade API contract."""
from abc import ABC, abstractmethod


class TokocryptoV3TradeApi(ABC):
    """Binance-standard signed spot trading + account (`/api/v3/*`).

    HMAC-SHA256 over the urlencoded query string, `X-MBX-APIKEY` header. Enum
    fields are the exchange's string values (`"BUY"`, `"LIMIT"`, `"GTC"`).
    Client orders are `newClientOrderId` on create and `origClientOrderId` on
    query/cancel; both of those also require `symbol`.
    """

    @abstractmethod
    async def create_order(self, *, symbol: str, side: str, type: str,
                           quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           price: str | None = None,
                           time_in_force: str | None = None,
                           new_client_order_id: str | None = None,
                           new_order_resp_type: str = "FULL") -> dict: ...

    @abstractmethod
    async def query_order(self, *, symbol: str, order_id: int | None = None,
                          orig_client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           orig_client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def open_orders(self, *, symbol: str | None = None) -> list: ...

    @abstractmethod
    async def my_trades(self, *, symbol: str, order_id: int | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, limit: int | None = None) -> list: ...

    @abstractmethod
    async def account(self) -> dict: ...
