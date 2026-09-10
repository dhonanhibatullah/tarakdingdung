from abc import ABC, abstractmethod


class SingleFlight(ABC):
    @abstractmethod
    async def acquire(self, key: str) -> bool: ...

    @abstractmethod
    async def release(self, key: str) -> None: ...
