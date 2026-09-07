"""Tokocrypto v3 market API contract."""
from abc import ABC, abstractmethod


class TokocryptoV3MarketApi(ABC):
    """Binance-standard public market data (`/api/v3/*` on the `.site` host).

    No authentication, no response envelope. `symbol` is the joined-upper form
    (`BTCIDR`). `interval` uses the Binance vocabulary (`1m`, `1h`, `1d`, …) —
    the same set the engine's `cron_interval` already uses, so it passes
    straight through with no mapping.
    """

    @abstractmethod
    async def server_time(self) -> dict: ...

    @abstractmethod
    async def exchange_info(self, *, symbol: str | None = None,
                            symbols: str | None = None) -> dict: ...

    @abstractmethod
    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> list: ...

    @abstractmethod
    async def depth(self, *, symbol: str, limit: int | None = None) -> dict: ...

    @abstractmethod
    async def ticker_price(self, *, symbol: str) -> dict: ...
