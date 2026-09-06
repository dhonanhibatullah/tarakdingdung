from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role


class RoleRepository(ABC):
    @abstractmethod
    async def create(self, *, name: str, description: str | None,
                     is_default: bool | None, created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> Role | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def read_default(self) -> Role | None: ...

    @abstractmethod
    async def read_permissions(self, role_id: UUID) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, name: str | None = None,
                           description: str | None = None, is_default: bool | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
