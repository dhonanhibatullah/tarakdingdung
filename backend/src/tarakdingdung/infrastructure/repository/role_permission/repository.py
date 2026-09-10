from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.infrastructure.repository.database.orm import RolePermissionRow


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: RolePermission) -> RolePermission:
        async with self._sessions() as session:
            row = RolePermissionRow(
                role_id=entity.role_id, permission_id=entity.permission_id
            )
            session.add(row)
            await session.commit()
            return entity

    async def read_by_role(self, role_id: str) -> list[RolePermission]:
        async with self._sessions() as session:
            stmt = select(RolePermissionRow).where(RolePermissionRow.role_id == role_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                RolePermission(role_id=r.role_id, permission_id=r.permission_id)
                for r in rows
            ]

    async def delete(self, role_id: str, permission_id: str) -> None:
        async with self._sessions() as session:
            stmt = delete(RolePermissionRow).where(
                RolePermissionRow.role_id == role_id,
                RolePermissionRow.permission_id == permission_id,
            )
            await session.execute(stmt)
            await session.commit()
