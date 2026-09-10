import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.symbol import SymbolRepository
from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.infrastructure.repository.database.orm import SymbolRow


def _to_domain(row: SymbolRow) -> Symbol:
    return Symbol(
        id=row.id, venue=row.venue, base=row.base, quote=row.quote, external=row.external
    )


class SqlAlchemySymbolRepository(SymbolRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Symbol) -> Symbol:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                SymbolRow(
                    id=id_,
                    venue=entity.venue,
                    base=entity.base,
                    quote=entity.quote,
                    external=entity.external,
                )
            )
            await session.commit()
        return Symbol(
            id=id_, venue=entity.venue, base=entity.base, quote=entity.quote, external=entity.external
        )

    async def read_by_id(self, id: str) -> Symbol | None:
        async with self._sessions() as session:
            row = await session.get(SymbolRow, id)
            return _to_domain(row) if row else None

    async def read_by_external(self, venue: str, external: str) -> Symbol | None:
        async with self._sessions() as session:
            stmt = select(SymbolRow).where(
                SymbolRow.venue == venue, SymbolRow.external == external
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[Symbol], int]:
        async with self._sessions() as session:
            base = select(SymbolRow)
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = base.order_by(SymbolRow.external).offset((page - 1) * per_page).limit(per_page)
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total
