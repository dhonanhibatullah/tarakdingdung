from abc import ABC, abstractmethod


class Password(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...

    @abstractmethod
    async def compare(self, stored_hash: str, password: str) -> None: ...
