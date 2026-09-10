from abc import ABC, abstractmethod

from tarakdingdung.domain.models.news import NewsArticle


class NewsSource(ABC):
    @abstractmethod
    async def fetch(self) -> list[NewsArticle]: ...
