import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)
from tarakdingdung.infrastructure.repository.database.orm import (
    SymbolRow,
    UniverseMembershipRow,
    UniverseRow,
)


def _to_domain(row: UniverseRow) -> Universe:
    return Universe(id=row.id, name=row.name)


def _membership_to_domain(row: UniverseMembershipRow) -> UniverseMembership:
    return UniverseMembership(
        universe_id=row.universe_id,
        symbol_id=row.symbol_id,
        state=MembershipState(row.state),
        rationale=row.rationale,
    )


def _symbol_to_domain(row: SymbolRow) -> Symbol:
    return Symbol(
        id=row.id, venue=row.venue, base=row.base, quote=row.quote, external=row.external
    )


class SqlAlchemyUniverseRepository(UniverseRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Universe) -> Universe:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(UniverseRow(id=id_, name=entity.name))
            await session.commit()
        return Universe(id=id_, name=entity.name)

    async def read_by_id(self, id: str) -> Universe | None:
        async with self._sessions() as session:
            row = await session.get(UniverseRow, id)
            return _to_domain(row) if row else None

    async def read_by_name(self, name: str) -> Universe | None:
        async with self._sessions() as session:
            stmt = select(UniverseRow).where(UniverseRow.name == name)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_memberships(self, universe_id: str) -> list[UniverseMembership]:
        async with self._sessions() as session:
            stmt = select(UniverseMembershipRow).where(
                UniverseMembershipRow.universe_id == universe_id
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_membership_to_domain(r) for r in rows]

    async def add_membership(self, entity: UniverseMembership) -> UniverseMembership:
        async with self._sessions() as session:
            session.add(
                UniverseMembershipRow(
                    universe_id=entity.universe_id,
                    symbol_id=entity.symbol_id,
                    state=entity.state.value,
                    rationale=entity.rationale,
                )
            )
            await session.commit()
        return entity

    async def update_membership(
        self,
        universe_id: str,
        symbol_id: str,
        state: MembershipState,
        rationale: str = "",
    ) -> UniverseMembership | None:
        async with self._sessions() as session:
            row = await session.get(UniverseMembershipRow, (universe_id, symbol_id))
            if row is None:
                return None
            row.state = state.value
            row.rationale = rationale
            await session.commit()
            return UniverseMembership(
                universe_id=universe_id,
                symbol_id=symbol_id,
                state=state,
                rationale=rationale,
            )

    async def read_symbols_by_state(
        self, universe_id: str, state: MembershipState
    ) -> list[Symbol]:
        async with self._sessions() as session:
            stmt = (
                select(SymbolRow)
                .join(
                    UniverseMembershipRow,
                    UniverseMembershipRow.symbol_id == SymbolRow.id,
                )
                .where(
                    UniverseMembershipRow.universe_id == universe_id,
                    UniverseMembershipRow.state == state.value,
                )
                .order_by(SymbolRow.external)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_symbol_to_domain(r) for r in rows]
