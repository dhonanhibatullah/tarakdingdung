from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, user_from_orm, user_list_item_from_orm,
)
from tarakdingdung.infrastructure.repository.shared.results import require, rows_affected
from tarakdingdung.infrastructure.repository.user import queries as q

_USERNAME_CONFLICT = ConflictMatch("username", ErrorType.USERNAME_EXISTS)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, role_id, name, bio, username, password_hash, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    new_id = await s.scalar(q.build_create(
                        role_id=role_id, name=name, bio=bio, username=username,
                        password_hash=password_hash, created_by=created_by))
                await self._db.persist(s)
                return require(new_id, "failed to create user")
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create user", exc, _USERNAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> User | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return user_from_orm(row) if row is not None else None

    async def read_by_username(self, username: str) -> User | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_username(username))).scalar_one_or_none()
        return user_from_orm(row) if row is not None else None

    async def read_permissions(self, user_id: UUID) -> list[Permission]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_permissions(user_id))).scalars().all()
        return [permission_from_orm(r) for r in rows]

    async def read_by_pagination(self, *, page, limit, search, role_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search, role_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_by_pagination(
                page=page, limit=limit, search=search, role_id=role_id))).all()
        return [user_list_item_from_orm(r.UserORM, r.role_name) for r in rows], int(total)

    async def update_by_id(self, id, *, role_id=None, name=None, bio=None, username=None,
                           password_hash=None, preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                async with s.begin_nested():
                    result = await s.execute(q.build_update_by_id(
                        id, role_id=role_id, name=name, bio=bio, username=username,
                        password_hash=password_hash, preferences=preferences,
                        updated_by=updated_by))
                await self._db.persist(s)
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update user", exc, _USERNAME_CONFLICT) from exc
        if rows_affected(result) == 0:
            raise DomainError("user not found", ErrorType.NOT_FOUND)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await self._db.persist(s)
        if rows_affected(result) == 0:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
