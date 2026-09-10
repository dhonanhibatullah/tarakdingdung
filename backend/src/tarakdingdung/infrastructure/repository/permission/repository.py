import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.infrastructure.repository.database.orm import PermissionRow


def _to_domain(row: PermissionRow) -> Permission:
    return Permission(id=row.id, name=row.name, description=row.description)


class SqlAlchemyPermissionRepository(PermissionRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Permission) -> Permission:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            row = PermissionRow(id=id_, name=entity.name, description=entity.description)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def read_by_id(self, id: str) -> Permission | None:
        async with self._sessions() as session:
            row = await session.get(PermissionRow, id)
            if row is None or row.is_deleted:
                return None
            return _to_domain(row)

    async def read_by_name(self, name: str) -> Permission | None:
        async with self._sessions() as session:
            stmt = select(PermissionRow).where(
                PermissionRow.name == name, PermissionRow.is_deleted.is_(False)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[Permission], int]:
        async with self._sessions() as session:
            base = select(PermissionRow).where(PermissionRow.is_deleted.is_(False))
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = (
                base.order_by(PermissionRow.name)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total

    async def update_by_id(self, id: str, entity: Permission) -> Permission | None:
        async with self._sessions() as session:
            row = await session.get(PermissionRow, id)
            if row is None or row.is_deleted:
                return None
            row.name = entity.name
            row.description = entity.description
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def delete_by_id(self, id: str) -> bool:
        async with self._sessions() as session:
            row = await session.get(PermissionRow, id)
            if row is None or row.is_deleted:
                return False
            row.is_deleted = True
            await session.commit()
            return True
