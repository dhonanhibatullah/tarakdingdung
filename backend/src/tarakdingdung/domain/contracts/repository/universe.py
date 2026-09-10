from abc import ABC, abstractmethod

from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)


class UniverseRepository(ABC):
    @abstractmethod
    async def create(self, entity: Universe) -> Universe: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Universe | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Universe | None: ...

    @abstractmethod
    async def read_memberships(self, universe_id: str) -> list[UniverseMembership]: ...

    @abstractmethod
    async def add_membership(self, entity: UniverseMembership) -> UniverseMembership: ...

    @abstractmethod
    async def update_membership(
        self, universe_id: str, symbol_id: str, state: MembershipState, rationale: str = ""
    ) -> UniverseMembership | None: ...

    @abstractmethod
    async def read_symbols_by_state(
        self, universe_id: str, state: MembershipState
    ) -> list[Symbol]: ...
