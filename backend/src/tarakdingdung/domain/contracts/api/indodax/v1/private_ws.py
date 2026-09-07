from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class IndodaxPrivateWebSocket(ABC):
    """Indodax authenticated WebSocket (`wss://pws.indodax.com/ws/`).

    The implementation first calls
    ``POST https://indodax.com/api/private_ws/v1/generate_token`` (HMAC-SHA512
    signed) to obtain a connection token and the account's private channel,
    then connects and subscribes. Yields order-update events.
    """

    @abstractmethod
    def stream(self) -> AsyncIterator[dict]:
        """Connect, authenticate, subscribe to the account's private channel
        and yield each decoded event. Refreshes the token and reconnects on
        expiry or connection loss.
        """
        ...
