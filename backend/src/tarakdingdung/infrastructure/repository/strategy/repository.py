from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.strategy import StrategyConfig
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.results import require, rows_affected
from tarakdingdung.infrastructure.repository.shared.trading import strategy_from_orm
from tarakdingdung.infrastructure.repository.strategy import queries as q

_NAME_CONFLICT = ConflictMatch("name", ErrorType.CONFLICT)


class SqlAlchemyStrategyRepository(StrategyRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, name, description, kind, mode, universe,
                     parameters, is_enabled, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    new_id = await s.scalar(q.build_create(
                        name=name, description=description, kind=kind, mode=mode,
                        universe=universe, parameters=parameters,
                        is_enabled=is_enabled, created_by=created_by))
                await self._db.persist(s)
                return require(new_id, "failed to create strategy")
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create strategy", exc, _NAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> StrategyConfig | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return strategy_from_orm(row) if row is not None else None

    async def read_by_name(self, name: str) -> StrategyConfig | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_name(name))).scalar_one_or_none()
        return strategy_from_orm(row) if row is not None else None

    async def read_enabled(self) -> list[StrategyConfig]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_enabled())).scalars().all()
        return [strategy_from_orm(r) for r in rows]

    async def read_by_pagination(self, *, page, limit, search, mode):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search, mode))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_by_pagination(
                page=page, limit=limit, search=search, mode=mode))).scalars().all()
        return [strategy_from_orm(r) for r in rows], int(total)

    async def update_by_id(self, id, *, name=None, description=None, kind=None,
                           mode=None, universe=None, parameters=None,
                           is_enabled=None, preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    result = await s.execute(q.build_update_by_id(
                        id, name=name, description=description, kind=kind, mode=mode,
                        universe=universe, parameters=parameters,
                        is_enabled=is_enabled, preferences=preferences,
                        updated_by=updated_by))
                await self._db.persist(s)
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update strategy", exc, _NAME_CONFLICT) from exc
        if rows_affected(result) == 0:
            raise DomainError("strategy not found", ErrorType.NOT_FOUND)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await self._db.persist(s)
        if rows_affected(result) == 0:
            raise DomainError("strategy not found", ErrorType.NOT_FOUND)
