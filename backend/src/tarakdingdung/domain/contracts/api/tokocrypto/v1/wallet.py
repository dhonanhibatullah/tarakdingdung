from abc import ABC, abstractmethod


class TokocryptoV1WalletApi(ABC):
    """Tokocrypto signed wallet REST API (`/open/v1/withdraws`,
    `/open/v1/deposits`, `/open/v1/deposits/address`).

    Same signing/unwrapping contract as ``TokocryptoV1TradeApi``. ``withdraw``
    requires the API key to hold the withdrawal permission.
    """

    @abstractmethod
    async def withdraw(self, *, asset: str, address: str, amount: str,
                       network: str | None = None, address_tag: str | None = None,
                       client_id: str | None = None) -> dict: ...

    @abstractmethod
    async def withdraw_history(self, *, asset: str | None = None, status: int | None = None,
                               from_id: int | None = None, start_time: int | None = None,
                               end_time: int | None = None) -> dict: ...

    @abstractmethod
    async def deposit_history(self, *, asset: str | None = None, status: int | None = None,
                              from_id: int | None = None, start_time: int | None = None,
                              end_time: int | None = None) -> dict: ...

    @abstractmethod
    async def deposit_address(self, *, asset: str, network: str) -> dict: ...
