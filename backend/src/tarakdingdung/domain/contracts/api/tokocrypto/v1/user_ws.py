from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TokocryptoUserWebSocket(ABC):
    """Tokocrypto authenticated user-data stream.

    The implementation obtains a listen token via
    ``POST /open/v1/user-listen-token``, connects to
    ``wss://stream-cloud.tokocrypto.site/stream?streams=<token>`` and keeps the
    token alive. Yields ``outboundAccountPosition`` and ``executionReport``
    events.
    """

    @abstractmethod
    def stream(self) -> AsyncIterator[dict]:
        """Acquire a listen token, connect and yield each decoded user event.
        Re-acquires the token and reconnects on expiry or connection loss.
        """
        ...
