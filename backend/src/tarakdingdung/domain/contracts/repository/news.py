from abc import ABC, abstractmethod

from tarakdingdung.domain.models.news import NewsAnalysis, NewsArticle


class NewsRepository(ABC):
    @abstractmethod
    async def create(self, entity: NewsArticle) -> NewsArticle: ...

    @abstractmethod
    async def create_analysis(self, entity: NewsAnalysis) -> NewsAnalysis: ...

    @abstractmethod
    async def read_recent(self, from_ms: int) -> list[NewsArticle]: ...

    @abstractmethod
    async def read_analyses(self, from_ms: int) -> list[NewsAnalysis]: ...
