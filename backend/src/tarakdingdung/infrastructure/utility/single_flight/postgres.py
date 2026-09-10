from collections.abc import Callable
from typing import Any

from sqlalchemy import text

from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight


class PostgresSingleFlight(SingleFlight):
    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory
        self._locks: dict[str, Any] = {}

    async def acquire(self, key: str) -> bool:
        session = self._session_factory()
        result = await session.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": key}
        )
        if result.scalar():
            self._locks[key] = session
            return True
        await session.close()
        return False

    async def release(self, key: str) -> None:
        session = self._locks.pop(key, None)
        if session is None:
            return
        await session.execute(
            text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": key}
        )
        await session.close()
