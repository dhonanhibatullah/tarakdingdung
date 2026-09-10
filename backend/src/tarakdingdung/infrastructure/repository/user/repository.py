import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.user import User
from tarakdingdung.infrastructure.repository.database.orm import UserRow


def _to_domain(row: UserRow) -> User:
    return User(
        id=row.id,
        username=row.username,
        email=row.email,
        password_hash=row.password_hash,
        is_active=row.is_active,
        is_deleted=row.is_deleted,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: User) -> User:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            row = UserRow(
                id=id_,
                username=entity.username,
                email=entity.email,
                password_hash=entity.password_hash,
                is_active=entity.is_active,
                is_deleted=entity.is_deleted,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def read_by_id(self, id: str) -> User | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, id)
            if row is None or row.is_deleted:
                return None
            return _to_domain(row)

    async def read_by_username(self, username: str) -> User | None:
        async with self._sessions() as session:
            stmt = select(UserRow).where(
                UserRow.username == username, UserRow.is_deleted.is_(False)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_by_email(self, email: str) -> User | None:
        async with self._sessions() as session:
            stmt = select(UserRow).where(
                UserRow.email == email, UserRow.is_deleted.is_(False)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[User], int]:
        async with self._sessions() as session:
            base = select(UserRow).where(UserRow.is_deleted.is_(False))
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = (
                base.order_by(UserRow.username)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total

    async def update_by_id(self, id: str, entity: User) -> User | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, id)
            if row is None or row.is_deleted:
                return None
            row.username = entity.username
            row.email = entity.email
            row.password_hash = entity.password_hash
            row.is_active = entity.is_active
            row.is_deleted = entity.is_deleted
            row.updated_at = entity.updated_at
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def delete_by_id(self, id: str) -> bool:
        async with self._sessions() as session:
            row = await session.get(UserRow, id)
            if row is None or row.is_deleted:
                return False
            row.is_deleted = True
            await session.commit()
            return True
