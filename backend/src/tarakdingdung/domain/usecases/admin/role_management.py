from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission


@dataclass(frozen=True, slots=True)
class CreateRoleRequest:
    name: str
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ReadRoleByIdRequest:
    id: UUID


@dataclass(frozen=True, slots=True)
class ReadRoleByNameRequest:
    name: str


@dataclass(frozen=True, slots=True)
class ReadDefaultRoleRequest:
    pass


@dataclass(frozen=True, slots=True)
class ReadRolePermissionsRequest:
    role_id: UUID


@dataclass(frozen=True, slots=True)
class ReadRolesByPaginationRequest:
    page: int
    limit: int
    search: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateRoleRequest:
    id: UUID
    name: str | None = None
    description: str | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class SetDefaultRoleRequest:
    id: UUID
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class DeleteRoleRequest:
    id: UUID
    deleted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AssignRolePermissionRequest:
    role_id: UUID
    permission_id: UUID
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RevokeRolePermissionRequest:
    role_id: UUID
    permission_id: UUID


@dataclass(frozen=True, slots=True)
class ReadRolePermissionByIdRequest:
    id: UUID


@dataclass(frozen=True, slots=True)
class ReadRolePermissionByRoleIdAndPermissionIdRequest:
    role_id: UUID
    permission_id: UUID


@dataclass(frozen=True, slots=True)
class ReadRolePermissionsByPaginationRequest:
    page: int
    limit: int
    role_id: UUID | None = None
    permission_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RolePermissionResult:
    role_permission: RolePermission
    role: Role
    permission: Permission


class RoleManagement(ABC):
    @abstractmethod
    async def create(self, request: CreateRoleRequest) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, request: ReadRoleByIdRequest) -> Role | None: ...

    @abstractmethod
    async def read_by_name(self, request: ReadRoleByNameRequest) -> Role | None: ...

    @abstractmethod
    async def read_default(self, request: ReadDefaultRoleRequest) -> Role | None: ...

    @abstractmethod
    async def read_permissions(self, request: ReadRolePermissionsRequest) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(
        self, request: ReadRolesByPaginationRequest
    ) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def update_by_id(self, request: UpdateRoleRequest) -> None: ...

    @abstractmethod
    async def set_default_role(self, request: SetDefaultRoleRequest) -> None: ...

    @abstractmethod
    async def delete_by_id(self, request: DeleteRoleRequest) -> None: ...

    @abstractmethod
    async def assign_permission(self, request: AssignRolePermissionRequest) -> UUID: ...

    @abstractmethod
    async def revoke_permission(self, request: RevokeRolePermissionRequest) -> None: ...

    @abstractmethod
    async def read_role_permission_by_id(
        self, request: ReadRolePermissionByIdRequest
    ) -> RolePermissionResult: ...

    @abstractmethod
    async def read_role_permission_by_role_id_and_permission_id(
        self, request: ReadRolePermissionByRoleIdAndPermissionIdRequest
    ) -> RolePermissionResult: ...

    @abstractmethod
    async def read_role_permissions_by_pagination(
        self, request: ReadRolePermissionsByPaginationRequest
    ) -> tuple[list[RolePermissionResult], int]: ...
