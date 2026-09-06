from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, DeleteUserRequest, ReadUserByIdRequest, ReadUserByUsernameRequest,
    ReadUserPermissionsRequest, ReadUsersByPaginationRequest, ResetUserPasswordRequest,
    UpdateUserRequest, UserManagement,
)


class UserManagementUsecase(UserManagement):
    _TAG = "admin/user_management"

    def __init__(self, *, users: UserRepository, password: Password,
                 logger: LeveledLogger) -> None:
        self._users = users
        self._password = password
        self._logger = logger

    async def _log(self, method: str, message: str, err: DomainError) -> None:
        await self._logger.error(f"{self._TAG}/{method}", message, {"err": err})

    async def create(self, request: CreateUserRequest) -> UUID:
        name = validation.required_person_name(request.name, "name")
        username = validation.required_username(request.username, "username")
        password = validation.required_password(request.password, "password")
        try:
            password_hash = await self._password.hash(password)
            return await self._users.create(
                role_id=request.role_id, name=name, bio=request.bio, username=username,
                password_hash=password_hash, created_by=request.created_by)
        except DomainError as err:
            await self._log("Create", "failed to create user", err)
            raise

    async def read_by_id(self, request: ReadUserByIdRequest) -> User | None:
        return await self._users.read_by_id(request.id)

    async def read_by_username(self, request: ReadUserByUsernameRequest) -> User | None:
        return await self._users.read_by_username(request.username)

    async def read_permissions(self, request: ReadUserPermissionsRequest) -> list[Permission]:
        return await self._users.read_permissions(request.user_id)

    async def read_by_pagination(
            self, request: ReadUsersByPaginationRequest) -> tuple[list[UserListItem], int]:
        return await self._users.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search,
            role_id=request.role_id)

    async def update_by_id(self, request: UpdateUserRequest) -> None:
        name = validation.optional_person_name(request.name, "name")
        username = validation.optional_username(request.username, "username")
        try:
            await self._users.update_by_id(
                request.id, role_id=request.role_id, name=name, bio=request.bio,
                username=username, updated_by=request.updated_by)
        except DomainError as err:
            await self._log("UpdateById", "failed to update user", err)
            raise

    async def reset_password(self, request: ResetUserPasswordRequest) -> None:
        password = validation.required_password(request.password, "password")
        try:
            password_hash = await self._password.hash(password)
            await self._users.update_by_id(request.id, password_hash=password_hash,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._log("ResetPassword", "failed to reset user password", err)
            raise

    async def delete_by_id(self, request: DeleteUserRequest) -> None:
        try:
            await self._users.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._log("DeleteById", "failed to delete user", err)
            raise
