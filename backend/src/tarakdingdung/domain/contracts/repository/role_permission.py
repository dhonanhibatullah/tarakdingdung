from abc import ABC, abstractmethod

from tarakdingdung.domain.models.role_permission import RolePermission


class RolePermissionRepository(ABC):
    @abstractmethod
    async def create(self, entity: RolePermission) -> RolePermission: ...

    @abstractmethod
    async def read_by_role(self, role_id: str) -> list[RolePermission]: ...

    @abstractmethod
    async def delete(self, role_id: str, permission_id: str) -> None: ...
