from abc import ABC, abstractmethod


class TokocryptoV1MarketApi(ABC):
    """Tokocrypto public market-data REST API (`/open/v1/common/*`,
    `/open/v1/market/*` on `https://www.tokocrypto.com`).

    No authentication. Responses are unwrapped from the
    ``{"code": 0, "msg": "", "data": ...}`` envelope; a non-zero ``code``
    raises. ``symbol`` follows the ``BTCIDR`` / ``BTCUSDT`` form.
    """

    @abstractmethod
    async def server_time(self) -> dict: ...

    @abstractmethod
    async def symbols(self) -> dict: ...

    @abstractmethod
    async def depth(self, *, symbol: str, limit: int | None = None) -> dict: ...

    @abstractmethod
    async def trades(self, *, symbol: str, from_id: int | None = None,
                     limit: int | None = None) -> dict: ...

    @abstractmethod
    async def agg_trades(self, *, symbol: str, from_id: int | None = None,
                         start_time: int | None = None, end_time: int | None = None,
                         limit: int | None = None) -> dict: ...

    @abstractmethod
    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> dict: ...
