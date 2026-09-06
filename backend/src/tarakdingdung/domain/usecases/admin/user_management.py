from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User, UserListItem


@dataclass(frozen=True, slots=True)
class CreateUserRequest:
    role_id: UUID
    name: str
    username: str
    password: str
    bio: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ReadUserByIdRequest:
    id: UUID


@dataclass(frozen=True, slots=True)
class ReadUserByUsernameRequest:
    username: str


@dataclass(frozen=True, slots=True)
class ReadUserPermissionsRequest:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ReadUsersByPaginationRequest:
    page: int
    limit: int
    search: str | None = None
    role_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateUserRequest:
    id: UUID
    role_id: UUID | None = None
    name: str | None = None
    bio: str | None = None
    username: str | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResetUserPasswordRequest:
    id: UUID
    password: str
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class DeleteUserRequest:
    id: UUID
    deleted_by: UUID | None = None


class UserManagement(ABC):
    @abstractmethod
    async def create(self, request: CreateUserRequest) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, request: ReadUserByIdRequest) -> User | None: ...

    @abstractmethod
    async def read_by_username(self, request: ReadUserByUsernameRequest) -> User | None: ...

    @abstractmethod
    async def read_permissions(self, request: ReadUserPermissionsRequest) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(
        self, request: ReadUsersByPaginationRequest
    ) -> tuple[list[UserListItem], int]: ...

    @abstractmethod
    async def update_by_id(self, request: UpdateUserRequest) -> None: ...

    @abstractmethod
    async def reset_password(self, request: ResetUserPasswordRequest) -> None: ...

    @abstractmethod
    async def delete_by_id(self, request: DeleteUserRequest) -> None: ...
