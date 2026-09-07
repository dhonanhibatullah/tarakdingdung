import hashlib

from sqlalchemy import text

from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.infrastructure.repository.database.session import Database


class PostgresSingleFlight(SingleFlight):
    """Cross-process mutual exclusion via Postgres advisory locks.

    Session-scoped rather than transaction-scoped, because a cycle spans many
    transactions and the lock must outlive each of them. The connection is held
    for the duration, so the lock is released if the worker dies — which is the
    property an in-process lock cannot offer and a row-based one would need a
    lease and a reaper to imitate.
    """

    def __init__(self, database: Database) -> None:
        self._db = database
        self._held: dict[str, object] = {}

    async def acquire(self, key: str) -> bool:
        connection = await self._db.engine.connect()
        try:
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": _key(key)})
        except Exception:
            await connection.close()
            raise
        if not acquired:
            await connection.close()
            return False
        self._held[key] = connection
        return True

    async def release(self, key: str) -> None:
        connection = self._held.pop(key, None)
        if connection is None:
            return
        try:
            await connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": _key(key)})
        finally:
            await connection.close()


def _key(key: str) -> int:
    """A stable signed 64-bit integer, which is all Postgres advisory locks take.

    Hashed rather than using Python's ``hash``, whose randomisation per process
    would give two workers different lock ids for the same key.
    """
    digest = hashlib.sha256(key.encode()).digest()[:8]
    return int.from_bytes(digest, "big", signed=True)
