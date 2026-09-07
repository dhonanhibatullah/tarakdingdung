from abc import ABC, abstractmethod


class IndodaxV2TradeApi(ABC):
    """Indodax Trade API v2 (`https://api.indodax.com/api/v2/*`).

    Binance-style REST. The implementation injects ``timestamp``/``recvWindow``,
    signs with HMAC-SHA256 (``X-APIKEY`` + ``Sign`` headers) and raises on the
    ``{"code": <negative>, "msg": ...}`` error shape. Requires a dedicated v2
    API key; trade/withdraw scopes need an IP allowlist.
    """

    @abstractmethod
    async def create_order(self, *, symbol: str, side: str, type: str,
                           price: str | None = None, quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           new_client_order_id: str | None = None,
                           time_in_force: str | None = None,
                           self_trade_prevention_mode: str | None = None) -> dict: ...

    @abstractmethod
    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def open_orders(self, *, symbol: str | None = None) -> list: ...

    @abstractmethod
    async def get_order(self, *, symbol: str, order_id: int | None = None,
                        client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def account(self, *, omit_zero_balances: bool | None = None) -> dict: ...

    @abstractmethod
    async def order_histories(self, *, symbol: str | None = None, limit: int | None = None,
                              start_time: int | None = None,
                              end_time: int | None = None) -> list: ...

    @abstractmethod
    async def my_trades(self, *, symbol: str, limit: int | None = None,
                        start_time: int | None = None,
                        end_time: int | None = None) -> list: ...

    @abstractmethod
    async def withdraw_history(self, *, coin: str | None = None, limit: int | None = None,
                               start_time: int | None = None, end_time: int | None = None,
                               withdraw_status: str | None = None) -> list: ...

    @abstractmethod
    async def deposit_history(self, *, coin: str | None = None,
                              start_time: int | None = None,
                              end_time: int | None = None) -> list: ...

    @abstractmethod
    async def deposit_address_list(self) -> list: ...

    @abstractmethod
    async def fiat_orders(self, *, start_time: int | None = None,
                          end_time: int | None = None) -> list: ...

    @abstractmethod
    async def withdraw_coin(self, *, asset: str, amount: str, address: str | None = None,
                            username: str | None = None,
                            network: str | None = None) -> dict: ...

    @abstractmethod
    async def withdraw_fiat(self, *, amount: str, bank_account_id: str) -> dict: ...
