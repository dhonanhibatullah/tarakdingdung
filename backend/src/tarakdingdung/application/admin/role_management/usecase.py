from __future__ import annotations
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.usecases.admin.role_management import AddRoleRequest, RoleManagement


class RoleManagementUsecase(RoleManagement):
    def __init__(
        self,
        roles: RoleRepository,
        permissions: PermissionRepository,
        role_permissions: RolePermissionRepository,
    ) -> None:
        self._roles = roles
        self._permissions = permissions
        self._role_permissions = role_permissions

    async def add(self, request: AddRoleRequest) -> Role:
        existing = await self._roles.read_by_name(request.name)
        if existing is not None:
            raise DomainError("role already exists", ErrorType.CONFLICT)
        return await self._roles.create(
            Role(
                id="",
                name=request.name,
                description=request.description,
                is_default=request.is_default,
            )
        )

    async def list(self, page: int, per_page: int) -> tuple[list[Role], int]:
        return await self._roles.read_by_pagination(page, per_page)

    async def assign_permission(self, role_id: str, permission_id: str) -> None:
        role = await self._roles.read_by_id(role_id)
        permission = await self._permissions.read_by_id(permission_id)
        if role is None or permission is None:
            raise DomainError("role or permission not found", ErrorType.NOT_FOUND)
        await self._role_permissions.create(
            RolePermission(role_id=role_id, permission_id=permission_id)
        )

    async def permissions(self, role_id: str) -> list[Permission]:
        return await self._roles.read_permissions(role_id)
