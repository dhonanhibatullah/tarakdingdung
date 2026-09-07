from abc import ABC, abstractmethod


class IndodaxV1PublicApi(ABC):
    """Indodax public market-data REST API (`https://indodax.com/api/*`).

    No authentication. All timestamps are milliseconds. `pair_id` follows the
    ``btcidr`` form; ``symbol`` (OHLC only) follows the ``BTCIDR`` form.
    """

    @abstractmethod
    async def server_time(self) -> dict: ...

    @abstractmethod
    async def pairs(self) -> list: ...

    @abstractmethod
    async def price_increments(self) -> dict: ...

    @abstractmethod
    async def summaries(self) -> dict: ...

    @abstractmethod
    async def ticker(self, pair_id: str = "btcidr") -> dict: ...

    @abstractmethod
    async def ticker_all(self) -> dict: ...

    @abstractmethod
    async def trades(self, pair_id: str = "btcidr") -> list: ...

    @abstractmethod
    async def depth(self, pair_id: str = "btcidr") -> dict: ...

    @abstractmethod
    async def ohlc(self, *, symbol: str, tf: str, from_ts: int, to_ts: int) -> list: ...
