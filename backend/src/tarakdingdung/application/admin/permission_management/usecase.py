from __future__ import annotations
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.usecases.admin.permission_management import (
    AddPermissionRequest,
    PermissionManagement,
)


class PermissionManagementUsecase(PermissionManagement):
    def __init__(self, permissions: PermissionRepository) -> None:
        self._permissions = permissions

    async def add(self, request: AddPermissionRequest) -> Permission:
        existing = await self._permissions.read_by_name(request.name)
        if existing is not None:
            raise DomainError("permission already exists", ErrorType.CONFLICT)
        return await self._permissions.create(
            Permission(id="", name=request.name, description=request.description)
        )

    async def list(self, page: int, per_page: int) -> tuple[list[Permission], int]:
        return await self._permissions.read_by_pagination(page, per_page)
