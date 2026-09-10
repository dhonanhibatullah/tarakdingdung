from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class Transactor(ABC):
    @abstractmethod
    async def __call__(self, fn: Callable[[Any], Awaitable[T]]) -> T: ...
