from abc import ABC, abstractmethod

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role


class RoleRepository(ABC):
    @abstractmethod
    async def create(self, entity: Role) -> Role: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Role | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def read_default(self) -> Role | None: ...

    @abstractmethod
    async def read_permissions(self, role_id: str) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def update_by_id(self, id: str, entity: Role) -> Role | None: ...

    @abstractmethod
    async def delete_by_id(self, id: str) -> bool: ...
