import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.models.news import NewsAnalysis, NewsArticle
from tarakdingdung.infrastructure.repository.database.orm import NewsAnalysisRow, NewsArticleRow


def _article_to_domain(row: NewsArticleRow) -> NewsArticle:
    return NewsArticle(
        id=row.id,
        source=row.source,
        url=row.url,
        title=row.title,
        published_ms=row.published_ms,
        raw_text=row.raw_text,
    )


def _analysis_to_domain(row: NewsAnalysisRow) -> NewsAnalysis:
    return NewsAnalysis(
        id=row.id, article_id=row.article_id, summary=row.summary, sentiment=row.sentiment
    )


class SqlAlchemyNewsRepository(NewsRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: NewsArticle) -> NewsArticle:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                NewsArticleRow(
                    id=id_,
                    source=entity.source,
                    url=entity.url,
                    title=entity.title,
                    published_ms=entity.published_ms,
                    raw_text=entity.raw_text,
                )
            )
            await session.commit()
        return NewsArticle(
            id=id_, source=entity.source, url=entity.url, title=entity.title,
            published_ms=entity.published_ms, raw_text=entity.raw_text,
        )

    async def create_analysis(self, entity: NewsAnalysis) -> NewsAnalysis:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                NewsAnalysisRow(
                    id=id_,
                    article_id=entity.article_id,
                    summary=entity.summary,
                    sentiment=entity.sentiment,
                )
            )
            await session.commit()
        return NewsAnalysis(
            id=id_, article_id=entity.article_id, summary=entity.summary, sentiment=entity.sentiment
        )

    async def read_recent(self, from_ms: int) -> list[NewsArticle]:
        async with self._sessions() as session:
            stmt = (
                select(NewsArticleRow)
                .where(NewsArticleRow.published_ms >= from_ms)
                .order_by(NewsArticleRow.published_ms.desc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_article_to_domain(r) for r in rows]

    async def read_analyses(self, from_ms: int) -> list[NewsAnalysis]:
        async with self._sessions() as session:
            stmt = (
                select(NewsAnalysisRow)
                .join(NewsArticleRow, NewsArticleRow.id == NewsAnalysisRow.article_id)
                .where(NewsArticleRow.published_ms >= from_ms)
                .order_by(NewsArticleRow.published_ms.desc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_analysis_to_domain(r) for r in rows]
