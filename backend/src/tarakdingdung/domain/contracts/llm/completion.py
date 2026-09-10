from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


class Completion(ABC):
    @abstractmethod
    async def complete(
        self, messages: list[Message], *, json_schema: str | None = None
    ) -> str: ...
