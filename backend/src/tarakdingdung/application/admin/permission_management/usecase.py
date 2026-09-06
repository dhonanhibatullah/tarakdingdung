from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, DeletePermissionRequest, PermissionManagement,
    ReadPermissionByIdRequest, ReadPermissionByNameRequest,
    ReadPermissionsByPaginationRequest, UpdatePermissionRequest,
)


class PermissionManagementUsecase(PermissionManagement):
    _TAG = "admin/permission_management"

    def __init__(self, *, permissions: PermissionRepository, logger: LeveledLogger) -> None:
        self._permissions = permissions
        self._logger = logger

    async def create(self, request: CreatePermissionRequest) -> UUID:
        name = validation.required_permission_name(request.name, "name")
        try:
            return await self._permissions.create(
                name=name, description=request.description, created_by=request.created_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Create", "failed to create permission",
                                     {"err": err})
            raise

    async def read_by_id(self, request: ReadPermissionByIdRequest) -> Permission | None:
        return await self._permissions.read_by_id(request.id)

    async def read_by_name(self, request: ReadPermissionByNameRequest) -> Permission | None:
        return await self._permissions.read_by_name(request.name)

    async def read_by_pagination(self, request: ReadPermissionsByPaginationRequest):
        return await self._permissions.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search)

    async def update_by_id(self, request: UpdatePermissionRequest) -> None:
        name = validation.optional_permission_name(request.name, "name")
        try:
            await self._permissions.update_by_id(
                request.id, name=name, description=request.description,
                updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/UpdateById", "failed to update permission",
                                     {"err": err})
            raise

    async def delete_by_id(self, request: DeletePermissionRequest) -> None:
        try:
            await self._permissions.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/DeleteById", "failed to delete permission",
                                     {"err": err})
            raise
