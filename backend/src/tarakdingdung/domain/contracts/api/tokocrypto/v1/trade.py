from abc import ABC, abstractmethod


class TokocryptoV1TradeApi(ABC):
    """Tokocrypto signed spot trading + account REST API (`/open/v1/orders*`,
    `/open/v1/account/*`).

    The implementation injects ``timestamp``/``recvWindow``, appends the
    HMAC-SHA256 ``signature`` and sends the ``X-MBX-APIKEY`` header, then
    unwraps ``data`` and raises on a non-zero ``code``. Enum fields
    (``side``, ``type``, ``time_in_force``, ``self_trade_prevention_mode``)
    use the exchange's integer codes.
    """

    @abstractmethod
    async def create_order(self, *, symbol: str, side: int, type: int,
                           quantity: str | None = None, quote_order_qty: str | None = None,
                           price: str | None = None, stop_price: str | None = None,
                           iceberg_qty: str | None = None, client_id: str | None = None,
                           time_in_force: int | None = None,
                           self_trade_prevention_mode: int | None = None) -> dict: ...

    @abstractmethod
    async def query_order(self, *, order_id: int | None = None,
                          client_id: str | None = None) -> dict: ...

    @abstractmethod
    async def cancel_order(self, *, order_id: int | None = None,
                           client_id: str | None = None) -> dict: ...

    @abstractmethod
    async def all_orders(self, *, symbol: str, type: int | None = None,
                         side: int | None = None, start_time: int | None = None,
                         end_time: int | None = None, from_id: str | None = None,
                         direct: str | None = None, limit: int | None = None) -> dict: ...

    @abstractmethod
    async def create_oco(self, *, symbol: str, side: int, quantity: str, price: str,
                         stop_price: str, stop_limit_price: str,
                         list_client_id: str | None = None,
                         limit_client_id: str | None = None,
                         stop_client_id: str | None = None) -> dict: ...

    @abstractmethod
    async def my_trades(self, *, symbol: str, order_id: str | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, direct: str | None = None,
                        limit: int | None = None) -> dict: ...

    @abstractmethod
    async def account(self) -> dict: ...

    @abstractmethod
    async def account_asset(self, *, asset: str) -> dict: ...
