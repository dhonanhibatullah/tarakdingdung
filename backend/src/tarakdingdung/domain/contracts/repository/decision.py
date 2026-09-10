from abc import ABC, abstractmethod

from tarakdingdung.domain.models.decision import Decision


class DecisionRepository(ABC):
    @abstractmethod
    async def create(self, entity: Decision) -> Decision: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Decision | None: ...

    @abstractmethod
    async def read_latest(self, universe_id: str) -> Decision | None: ...

    @abstractmethod
    async def read_range(
        self, universe_id: str, from_ms: int, to_ms: int
    ) -> list[Decision]: ...
