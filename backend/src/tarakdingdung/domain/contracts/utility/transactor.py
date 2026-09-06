from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class Transactor(ABC):
    @abstractmethod
    async def run(self, fn: Callable[[], Awaitable[T]]) -> T: ...
