from abc import ABC, abstractmethod


class SingleFlight(ABC):
    """Ensures one holder at a time for a named piece of work.

    Two overlapping cycles on one strategy would each size against a portfolio
    the other is about to change. Implementations must coordinate *across
    processes* — a lock local to one worker silently stops working the moment a
    second worker exists, while still appearing correct in tests.

    ``acquire`` returns False rather than waiting: a cycle that arrives while
    the previous one is still running should be skipped, not queued, because by
    the time it ran its snapshot would be stale anyway.
    """

    @abstractmethod
    async def acquire(self, key: str) -> bool: ...

    @abstractmethod
    async def release(self, key: str) -> None: ...
