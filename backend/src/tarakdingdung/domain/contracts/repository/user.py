from abc import ABC, abstractmethod

from tarakdingdung.domain.models.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, entity: User) -> User: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> User | None: ...

    @abstractmethod
    async def read_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def read_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[User], int]: ...

    @abstractmethod
    async def update_by_id(self, id: str, entity: User) -> User | None: ...

    @abstractmethod
    async def delete_by_id(self, id: str) -> bool: ...
