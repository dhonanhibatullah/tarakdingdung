from tarakdingdung.domain.contracts.repository.symbol import SymbolRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    UniverseMembership,
)
from tarakdingdung.domain.usecases.trading.universe import Universe


class UniverseUsecase(Universe):
    def __init__(
        self, universes: UniverseRepository, symbols: SymbolRepository
    ) -> None:
        self._universes = universes
        self._symbols = symbols

    async def list(self, universe_id: str) -> list[Symbol]:
        return await self._universes.read_symbols_by_state(
            universe_id, MembershipState.APPROVED
        )

    async def propose(
        self, universe_id: str, symbol: Symbol, rationale: str = ""
    ) -> UniverseMembership:
        existing = await self._symbols.read_by_external(symbol.venue, symbol.external)
        if existing is None:
            existing = await self._symbols.create(symbol)
        return await self._universes.add_membership(
            UniverseMembership(
                universe_id=universe_id,
                symbol_id=existing.id,
                state=MembershipState.PROPOSED,
                rationale=rationale,
            )
        )

    async def approve(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership:
        return await self._universes.update_membership(
            universe_id, symbol_id, MembershipState.APPROVED, rationale
        )

    async def reject(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership:
        return await self._universes.update_membership(
            universe_id, symbol_id, MembershipState.REJECTED, rationale
        )

    async def remove(
        self, universe_id: str, symbol_id: str, rationale: str = ""
    ) -> UniverseMembership:
        return await self._universes.update_membership(
            universe_id, symbol_id, MembershipState.REMOVED, rationale
        )
