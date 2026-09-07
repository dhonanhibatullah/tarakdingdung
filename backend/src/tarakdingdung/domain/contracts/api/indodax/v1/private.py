from abc import ABC, abstractmethod


class IndodaxV1PrivateApi(ABC):
    """Indodax legacy Trade API v1 ("tapi", `POST https://indodax.com/tapi`).

    Every call is a signed POST that dispatches on a ``method`` field; the
    implementation injects ``timestamp``/``recvWindow`` and the HMAC-SHA512
    ``Sign`` header, unwraps ``return`` on success and raises on
    ``{"success": 0}``. Methods map 1:1 to the documented ``method`` values.
    """

    @abstractmethod
    async def get_info(self) -> dict: ...

    @abstractmethod
    async def trans_history(self, *, start: str | None = None,
                            end: str | None = None) -> dict: ...

    @abstractmethod
    async def trade(self, *, pair: str, type: str, price: str | None = None,
                    idr: str | None = None, coin_amount: str | None = None,
                    order_type: str | None = None, client_order_id: str | None = None,
                    time_in_force: str | None = None,
                    smp_cancel: str | None = None) -> dict: ...

    @abstractmethod
    async def trade_history(self, *, pair: str, count: int | None = None,
                            from_id: int | None = None, end_id: int | None = None,
                            order: str | None = None, since: int | None = None,
                            end: int | None = None, order_id: int | None = None) -> dict: ...

    @abstractmethod
    async def open_orders(self, *, pair: str | None = None) -> dict: ...

    @abstractmethod
    async def order_history(self, *, pair: str, count: int | None = None,
                            from_: int | None = None) -> dict: ...

    @abstractmethod
    async def get_order(self, *, pair: str, order_id: int) -> dict: ...

    @abstractmethod
    async def get_order_by_client_order_id(self, *, client_order_id: str) -> dict: ...

    @abstractmethod
    async def cancel_order(self, *, pair: str, order_id: int, type: str,
                           order_type: str | None = None) -> dict: ...

    @abstractmethod
    async def cancel_by_client_order_id(self, *, client_order_id: str) -> dict: ...

    @abstractmethod
    async def withdraw_fee(self, *, currency: str, network: str | None = None) -> dict: ...

    @abstractmethod
    async def withdraw_coin(self, *, currency: str, withdraw_amount: str, request_id: str,
                            network: str | None = None, withdraw_address: str | None = None,
                            withdraw_memo: str | None = None,
                            withdraw_input_method: str | None = None,
                            withdraw_username: str | None = None) -> dict: ...

    @abstractmethod
    async def list_downline(self, *, page: int, limit: int) -> dict: ...

    @abstractmethod
    async def check_downline(self, *, email: str) -> dict: ...

    @abstractmethod
    async def create_voucher(self, *, amount: int, to_email: str) -> dict: ...
