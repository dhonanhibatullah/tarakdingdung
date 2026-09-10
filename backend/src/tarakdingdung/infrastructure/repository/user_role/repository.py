from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.user_role import UserRoleRepository
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user_role import UserRole
from tarakdingdung.infrastructure.repository.database.orm import RoleRow, UserRoleRow


def _role_to_domain(row: RoleRow) -> Role:
    return Role(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
    )


class SqlAlchemyUserRoleRepository(UserRoleRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: UserRole) -> UserRole:
        async with self._sessions() as session:
            row = UserRoleRow(user_id=entity.user_id, role_id=entity.role_id)
            session.add(row)
            await session.commit()
            return entity

    async def read_by_user(self, user_id: str) -> list[UserRole]:
        async with self._sessions() as session:
            stmt = select(UserRoleRow).where(UserRoleRow.user_id == user_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [UserRole(user_id=r.user_id, role_id=r.role_id) for r in rows]

    async def read_roles_by_user(self, user_id: str) -> list[Role]:
        async with self._sessions() as session:
            stmt = (
                select(RoleRow)
                .join(UserRoleRow, UserRoleRow.role_id == RoleRow.id)
                .where(UserRoleRow.user_id == user_id, RoleRow.is_deleted.is_(False))
                .order_by(RoleRow.name)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_role_to_domain(r) for r in rows]

    async def delete(self, user_id: str, role_id: str) -> None:
        async with self._sessions() as session:
            stmt = delete(UserRoleRow).where(
                UserRoleRow.user_id == user_id, UserRoleRow.role_id == role_id
            )
            await session.execute(stmt)
            await session.commit()
