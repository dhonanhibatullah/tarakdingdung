from abc import ABC, abstractmethod

from tarakdingdung.domain.models.news import NewsAnalysis


class NewsSummarizer(ABC):
    @abstractmethod
    async def summarize(self) -> NewsAnalysis | None: ...
