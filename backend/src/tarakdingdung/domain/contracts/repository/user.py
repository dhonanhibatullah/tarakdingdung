from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User, UserListItem


class UserRepository(ABC):
    @abstractmethod
    async def create(self, *, role_id: UUID, name: str, bio: str | None, username: str,
                     password_hash: str, created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> User | None: ...

    @abstractmethod
    async def read_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def read_permissions(self, user_id: UUID) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int, search: str | None,
                                 role_id: UUID | None) -> tuple[list[UserListItem], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, role_id: UUID | None = None,
                           name: str | None = None, bio: str | None = None,
                           username: str | None = None, password_hash: str | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
