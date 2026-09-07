from abc import ABC, abstractmethod


class TokocryptoV1StreamApi(ABC):
    """Tokocrypto user-data-stream token REST API
    (`POST /open/v1/user-listen-token`).

    Returns a listen token used to open the authenticated WebSocket user
    stream. Replaces the deprecated `/open/v1/user-data-stream` listen-key
    endpoints (decommissioned 2026-04-30).
    """

    @abstractmethod
    async def create_listen_token(self, *, validity: int | None = None) -> dict: ...
