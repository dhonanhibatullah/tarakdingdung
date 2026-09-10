from abc import ABC, abstractmethod

from tarakdingdung.domain.models.symbol import Symbol


class SymbolRepository(ABC):
    @abstractmethod
    async def create(self, entity: Symbol) -> Symbol: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Symbol | None: ...

    @abstractmethod
    async def read_by_external(self, venue: str, external: str) -> Symbol | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[Symbol], int]: ...
