from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence


class TokocryptoMarketWebSocket(ABC):
    """Tokocrypto public market-data streams
    (`wss://stream-cloud.tokocrypto.site/stream`).

    Stream names follow the Binance form: ``<symbol>@aggTrade``, ``<symbol>@trade``,
    ``<symbol>@kline_<interval>``, ``<symbol>@miniTicker``, ``<symbol>@depth``,
    ``<symbol>@depth<levels>`` (lower-case symbol, e.g. ``btcusdt``).
    """

    @abstractmethod
    def stream(self, streams: Sequence[str]) -> AsyncIterator[dict]:
        """Connect, send a ``SUBSCRIBE`` frame for ``streams`` and yield each
        decoded stream message. Reconnects and re-subscribes on loss.
        """
        ...
