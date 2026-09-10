from abc import ABC, abstractmethod

from tarakdingdung.domain.models.symbol import Symbol, UniverseMembership


class Universe(ABC):
    @abstractmethod
    async def list(self, universe_id: str) -> list[Symbol]: ...

    @abstractmethod
    async def propose(
        self, universe_id: str, symbol: Symbol, rationale: str = ""
    ) -> UniverseMembership: ...

    @abstractmethod
    async def approve(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership: ...

    @abstractmethod
    async def reject(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership: ...

    @abstractmethod
    async def remove(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership: ...
