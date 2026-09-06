from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission


class PermissionRepository(ABC):
    @abstractmethod
    async def create(self, *, name: str, description: str | None,
                     created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> Permission | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Permission | None: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None) -> tuple[list[Permission], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, name: str | None = None,
                           description: str | None = None, preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
