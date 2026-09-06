from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission

RolePermissionRow = tuple[RolePermission, Role, Permission]


class RolePermissionRepository(ABC):
    @abstractmethod
    async def create(self, *, role_id: UUID, permission_id: UUID,
                     created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> RolePermissionRow | None: ...

    @abstractmethod
    async def read_by_role_id_and_permission_id(
        self, role_id: UUID, permission_id: UUID) -> RolePermissionRow | None: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int, role_id: UUID | None,
                                 permission_id: UUID | None
                                 ) -> tuple[list[RolePermissionRow], int]: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID) -> None: ...

    @abstractmethod
    async def delete_by_role_id_and_permission_id(
        self, *, role_id: UUID | None, permission_id: UUID | None) -> None: ...
