from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.role_permission import (
    RolePermissionRepository, RolePermissionRow,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.role_permission import queries as q
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, role_from_orm, role_permission_from_orm,
)

_PAIR_CONFLICT = ConflictMatch("role_permission", ErrorType.ROLE_PERMISSION_EXISTS)


def _row(rp, role, perm) -> RolePermissionRow:
    return (role_permission_from_orm(rp), role_from_orm(role), permission_from_orm(perm))


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, role_id, permission_id, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    new_id = await s.scalar(q.build_create(
                        role_id=role_id, permission_id=permission_id, created_by=created_by))
                await self._db.persist(s)
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to assign role permission", exc, _PAIR_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> RolePermissionRow | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).first()
        return _row(*row) if row is not None else None

    async def read_by_role_id_and_permission_id(self, role_id, permission_id):
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_pair(role_id, permission_id))).first()
        return _row(*row) if row is not None else None

    async def read_by_pagination(self, *, page, limit, role_id, permission_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(role_id, permission_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_by_pagination(
                page=page, limit=limit, role_id=role_id, permission_id=permission_id))).all()
        return [_row(*r) for r in rows], int(total)

    async def delete_by_id(self, id: UUID) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_delete_by_id(id))
            if result.rowcount == 0:
                raise DomainError("role permission not found", ErrorType.NOT_FOUND)
            await self._db.persist(s)

    async def delete_by_role_id_and_permission_id(self, *, role_id, permission_id) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_delete_by_pair(role_id, permission_id))
            if result.rowcount == 0:
                raise DomainError("role permission not found", ErrorType.NOT_FOUND)
            await self._db.persist(s)
