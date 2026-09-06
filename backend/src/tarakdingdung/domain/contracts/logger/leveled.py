from abc import ABC, abstractmethod


class LeveledLogger(ABC):
    @abstractmethod
    async def error(self, tag: str, message: str, meta: dict) -> None: ...

    @abstractmethod
    async def warn(self, tag: str, message: str, meta: dict) -> None: ...

    @abstractmethod
    async def info(self, tag: str, message: str, meta: dict) -> None: ...

    @abstractmethod
    async def debug(self, tag: str, message: str, meta: dict) -> None: ...
