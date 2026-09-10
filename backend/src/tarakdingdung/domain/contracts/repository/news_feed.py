from abc import ABC, abstractmethod

from tarakdingdung.domain.models.news import NewsFeed


class NewsFeedRepository(ABC):
    @abstractmethod
    async def create(self, entity: NewsFeed) -> NewsFeed: ...

    @abstractmethod
    async def read_by_url(self, url: str) -> NewsFeed | None: ...

    @abstractmethod
    async def read_enabled(self) -> list[NewsFeed]: ...

    @abstractmethod
    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[NewsFeed], int]: ...
