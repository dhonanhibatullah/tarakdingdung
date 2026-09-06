from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, CreateRoleRequest, DeleteRoleRequest, ReadDefaultRoleRequest,
    ReadRoleByIdRequest, ReadRoleByNameRequest, ReadRolePermissionByIdRequest,
    ReadRolePermissionByRoleIdAndPermissionIdRequest, ReadRolePermissionsByPaginationRequest,
    ReadRolePermissionsRequest, ReadRolesByPaginationRequest, RevokeRolePermissionRequest,
    RoleManagement, RolePermissionResult, SetDefaultRoleRequest, UpdateRoleRequest,
)


class RoleManagementUsecase(RoleManagement):
    _TAG = "admin/role_management"

    def __init__(self, *, roles: RoleRepository,
                 role_permissions: RolePermissionRepository, logger: LeveledLogger) -> None:
        self._roles = roles
        self._role_permissions = role_permissions
        self._logger = logger

    async def _log(self, method: str, message: str, err: DomainError) -> None:
        await self._logger.error(f"{self._TAG}/{method}", message, {"err": err})

    async def create(self, request: CreateRoleRequest) -> UUID:
        name = validation.required_role_name(request.name, "name")
        try:
            return await self._roles.create(name=name, description=request.description,
                                            is_default=None, created_by=request.created_by)
        except DomainError as err:
            await self._log("Create", "failed to create role", err)
            raise

    async def read_by_id(self, request: ReadRoleByIdRequest) -> Role | None:
        return await self._roles.read_by_id(request.id)

    async def read_by_name(self, request: ReadRoleByNameRequest) -> Role | None:
        return await self._roles.read_by_name(request.name)

    async def read_default(self, request: ReadDefaultRoleRequest) -> Role | None:
        return await self._roles.read_default()

    async def read_permissions(self, request: ReadRolePermissionsRequest) -> list[Permission]:
        return await self._roles.read_permissions(request.role_id)

    async def read_by_pagination(
            self, request: ReadRolesByPaginationRequest) -> tuple[list[Role], int]:
        return await self._roles.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search)

    async def update_by_id(self, request: UpdateRoleRequest) -> None:
        name = validation.optional_role_name(request.name, "name")
        try:
            await self._roles.update_by_id(request.id, name=name, description=request.description,
                                           is_default=None, updated_by=request.updated_by)
        except DomainError as err:
            await self._log("UpdateById", "failed to update role", err)
            raise

    async def set_default_role(self, request: SetDefaultRoleRequest) -> None:
        try:
            await self._roles.update_by_id(request.id, is_default=True,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._log("SetDefaultRole", "failed to set default role", err)
            raise

    async def delete_by_id(self, request: DeleteRoleRequest) -> None:
        try:
            await self._roles.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._log("DeleteById", "failed to delete role", err)
            raise

    async def assign_permission(self, request: AssignRolePermissionRequest) -> UUID:
        try:
            return await self._role_permissions.create(
                role_id=request.role_id, permission_id=request.permission_id,
                created_by=request.created_by)
        except DomainError as err:
            await self._log("AssignPermission", "failed to assign role permission", err)
            raise

    async def revoke_permission(self, request: RevokeRolePermissionRequest) -> None:
        try:
            await self._role_permissions.delete_by_role_id_and_permission_id(
                role_id=request.role_id, permission_id=request.permission_id)
        except DomainError as err:
            await self._log("RevokePermission", "failed to revoke role permission", err)
            raise

    async def read_role_permission_by_id(
            self, request: ReadRolePermissionByIdRequest) -> RolePermissionResult:
        row = await self._role_permissions.read_by_id(request.id)
        if row is None:
            raise DomainError("role permission not found", ErrorType.NOT_FOUND)
        return RolePermissionResult(*row)

    async def read_role_permission_by_role_id_and_permission_id(
            self, request: ReadRolePermissionByRoleIdAndPermissionIdRequest,
    ) -> RolePermissionResult:
        row = await self._role_permissions.read_by_role_id_and_permission_id(
            request.role_id, request.permission_id)
        if row is None:
            raise DomainError("role permission not found", ErrorType.NOT_FOUND)
        return RolePermissionResult(*row)

    async def read_role_permissions_by_pagination(
            self, request: ReadRolePermissionsByPaginationRequest,
    ) -> tuple[list[RolePermissionResult], int]:
        rows, total = await self._role_permissions.read_by_pagination(
            page=request.page, limit=request.limit,
            role_id=request.role_id, permission_id=request.permission_id)
        results = [RolePermissionResult(*row) for row in rows]
        return results, total
