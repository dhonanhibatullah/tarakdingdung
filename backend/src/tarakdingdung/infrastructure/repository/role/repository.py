from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.role import queries as q
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, role_from_orm,
)

_NAME_CONFLICT = ConflictMatch("name", ErrorType.ROLE_NAME_EXISTS)


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, name, description, is_default, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    if is_default:
                        await s.execute(q.build_unset_defaults(created_by))
                    new_id = await s.scalar(q.build_create(
                        name=name, description=description,
                        is_default=is_default, created_by=created_by))
                await self._db.persist(s)
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create role", exc, _NAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_by_name(self, name: str) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_name(name))).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_default(self) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_default())).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_permissions(self, role_id: UUID) -> list[Permission]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_permissions(role_id))).scalars().all()
        return [permission_from_orm(r) for r in rows]

    async def read_by_pagination(self, *, page, limit, search):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search))
            if not total:
                return [], 0
            rows = (await s.execute(
                q.build_read_by_pagination(page=page, limit=limit, search=search))).scalars().all()
        return [role_from_orm(r) for r in rows], int(total)

    async def update_by_id(self, id, *, name=None, description=None, is_default=None,
                           preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    if is_default:
                        await s.execute(q.build_unset_defaults(updated_by, except_id=id))
                    result = await s.execute(q.build_update_by_id(
                        id, name=name, description=description, is_default=is_default,
                        preferences=preferences, updated_by=updated_by))
                    if result.rowcount == 0:
                        raise DomainError("role not found", ErrorType.NOT_FOUND)
                await self._db.persist(s)
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update role", exc, _NAME_CONFLICT) from exc

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await self._db.persist(s)
        if result.rowcount == 0:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
