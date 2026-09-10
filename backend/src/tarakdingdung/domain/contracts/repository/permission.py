from abc import ABC, abstractmethod

from tarakdingdung.domain.models.permission import Permission


class PermissionRepository(ABC):
    @abstractmethod
    async def create(self, entity: Permission) -> Permission: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Permission | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Permission | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[Permission], int]: ...

    @abstractmethod
    async def update_by_id(self, id: str, entity: Permission) -> Permission | None: ...

    @abstractmethod
    async def delete_by_id(self, id: str) -> bool: ...
