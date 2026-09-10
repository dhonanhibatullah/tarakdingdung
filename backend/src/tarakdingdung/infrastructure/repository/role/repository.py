import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionRow,
    RolePermissionRow,
    RoleRow,
)


def _to_domain(row: RoleRow) -> Role:
    return Role(
        id=row.id,
        name=row.name,
        description=row.description,
        is_default=row.is_default,
    )


def _perm_to_domain(row: PermissionRow) -> Permission:
    return Permission(id=row.id, name=row.name, description=row.description)


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Role) -> Role:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            row = RoleRow(
                id=id_,
                name=entity.name,
                description=entity.description,
                is_default=entity.is_default,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def read_by_id(self, id: str) -> Role | None:
        async with self._sessions() as session:
            row = await session.get(RoleRow, id)
            if row is None or row.is_deleted:
                return None
            return _to_domain(row)

    async def read_by_name(self, name: str) -> Role | None:
        async with self._sessions() as session:
            stmt = select(RoleRow).where(
                RoleRow.name == name, RoleRow.is_deleted.is_(False)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_default(self) -> Role | None:
        async with self._sessions() as session:
            stmt = select(RoleRow).where(
                RoleRow.is_default.is_(True), RoleRow.is_deleted.is_(False)
            )
            row = (await session.execute(stmt)).scalars().first()
            return _to_domain(row) if row else None

    async def read_permissions(self, role_id: str) -> list[Permission]:
        async with self._sessions() as session:
            stmt = (
                select(PermissionRow)
                .join(
                    RolePermissionRow,
                    RolePermissionRow.permission_id == PermissionRow.id,
                )
                .where(
                    RolePermissionRow.role_id == role_id,
                    PermissionRow.is_deleted.is_(False),
                )
                .order_by(PermissionRow.name)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_perm_to_domain(r) for r in rows]

    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[Role], int]:
        async with self._sessions() as session:
            base = select(RoleRow).where(RoleRow.is_deleted.is_(False))
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = (
                base.order_by(RoleRow.name).offset((page - 1) * per_page).limit(per_page)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total

    async def update_by_id(self, id: str, entity: Role) -> Role | None:
        async with self._sessions() as session:
            row = await session.get(RoleRow, id)
            if row is None or row.is_deleted:
                return None
            row.name = entity.name
            row.description = entity.description
            row.is_default = entity.is_default
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def delete_by_id(self, id: str) -> bool:
        async with self._sessions() as session:
            row = await session.get(RoleRow, id)
            if row is None or row.is_deleted:
                return False
            row.is_deleted = True
            await session.commit()
            return True
