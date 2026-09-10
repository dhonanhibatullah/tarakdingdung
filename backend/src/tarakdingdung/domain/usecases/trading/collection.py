from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CollectResult:
    failed: list[str] = field(default_factory=list)


class Collection(ABC):
    @abstractmethod
    async def collect(self) -> CollectResult: ...
