from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission


@dataclass(frozen=True, slots=True)
class CreatePermissionRequest:
    name: str
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ReadPermissionByIdRequest:
    id: UUID


@dataclass(frozen=True, slots=True)
class ReadPermissionByNameRequest:
    name: str


@dataclass(frozen=True, slots=True)
class ReadPermissionsByPaginationRequest:
    page: int
    limit: int
    search: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePermissionRequest:
    id: UUID
    name: str | None = None
    description: str | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class DeletePermissionRequest:
    id: UUID
    deleted_by: UUID | None = None


class PermissionManagement(ABC):
    @abstractmethod
    async def create(self, request: CreatePermissionRequest) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, request: ReadPermissionByIdRequest) -> Permission | None: ...

    @abstractmethod
    async def read_by_name(self, request: ReadPermissionByNameRequest) -> Permission | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, request: ReadPermissionsByPaginationRequest
    ) -> tuple[list[Permission], int]: ...

    @abstractmethod
    async def update_by_id(self, request: UpdatePermissionRequest) -> None: ...

    @abstractmethod
    async def delete_by_id(self, request: DeletePermissionRequest) -> None: ...
