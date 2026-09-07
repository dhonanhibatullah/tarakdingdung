from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence


class IndodaxMarketWebSocket(ABC):
    """Indodax public market-data WebSocket (`wss://ws3.indodax.com/ws/`).

    Channels follow the documented forms: ``chart:tick-<pair>``,
    ``market:summary-24h``, ``market:trade-activity-<pair>``,
    ``market:order-book-<pair>`` (``<pair>`` like ``btcidr``).
    """

    @abstractmethod
    def stream(self, channels: Sequence[str]) -> AsyncIterator[dict]:
        """Connect, authenticate with the static token, subscribe to
        ``channels`` and yield each decoded push message. Reconnects and
        re-subscribes transparently on connection loss.
        """
        ...
