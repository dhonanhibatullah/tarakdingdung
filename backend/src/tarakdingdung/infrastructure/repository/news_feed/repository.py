import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.news_feed import NewsFeedRepository
from tarakdingdung.domain.models.news import NewsFeed
from tarakdingdung.infrastructure.repository.database.orm import NewsFeedRow


def _to_domain(row: NewsFeedRow) -> NewsFeed:
    return NewsFeed(id=row.id, name=row.name, url=row.url, enabled=row.enabled)


class SqlAlchemyNewsFeedRepository(NewsFeedRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: NewsFeed) -> NewsFeed:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                NewsFeedRow(
                    id=id_, name=entity.name, url=entity.url, enabled=entity.enabled
                )
            )
            await session.commit()
        return NewsFeed(id=id_, name=entity.name, url=entity.url, enabled=entity.enabled)

    async def read_by_url(self, url: str) -> NewsFeed | None:
        async with self._sessions() as session:
            stmt = select(NewsFeedRow).where(NewsFeedRow.url == url)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_enabled(self) -> list[NewsFeed]:
        async with self._sessions() as session:
            stmt = (
                select(NewsFeedRow)
                .where(NewsFeedRow.enabled.is_(True))
                .order_by(NewsFeedRow.name)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows]

    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[NewsFeed], int]:
        async with self._sessions() as session:
            base = select(NewsFeedRow)
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = base.order_by(NewsFeedRow.name).offset((page - 1) * per_page).limit(per_page)
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total
