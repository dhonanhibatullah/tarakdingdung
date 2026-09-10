from __future__ import annotations
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.repository.user_role import UserRoleRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.models.user_role import UserRole
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest, UserManagement


class UserManagementUsecase(UserManagement):
    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        user_roles: UserRoleRepository,
        password: Password,
    ) -> None:
        self._users = users
        self._roles = roles
        self._user_roles = user_roles
        self._password = password

    async def add(self, request: AddUserRequest) -> User:
        if await self._users.read_by_username(request.username) is not None:
            raise DomainError("username already exists", ErrorType.CONFLICT)
        if await self._users.read_by_email(request.email) is not None:
            raise DomainError("email already exists", ErrorType.CONFLICT)

        password_hash = self._password.hash(request.password)
        user = await self._users.create(
            User(
                id="",
                username=request.username,
                email=request.email,
                password_hash=password_hash,
            )
        )
        for role_name in request.role_names:
            role = await self._roles.read_by_name(role_name)
            if role is None:
                raise DomainError(f"role not found: {role_name}", ErrorType.NOT_FOUND)
            await self._user_roles.create(UserRole(user_id=user.id, role_id=role.id))
        return user

    async def list(self, page: int, per_page: int) -> tuple[list[User], int]:
        return await self._users.read_by_pagination(page, per_page)

    async def deactivate(self, user_id: str) -> User:
        user = await self._users.read_by_id(user_id)
        if user is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        updated = User(
            id=user.id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            is_active=False,
            is_deleted=user.is_deleted,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        result = await self._users.update_by_id(user_id, updated)
        if result is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        return result
