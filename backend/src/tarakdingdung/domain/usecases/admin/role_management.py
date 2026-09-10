from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role


@dataclass(frozen=True, slots=True)
class AddRoleRequest:
    name: str
    description: str = ""
    is_default: bool = False


class RoleManagement(ABC):
    @abstractmethod
    async def add(self, request: AddRoleRequest) -> Role: ...

    @abstractmethod
    async def list(self, page: int, per_page: int) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def assign_permission(self, role_id: str, permission_id: str) -> None: ...

    @abstractmethod
    async def permissions(self, role_id: str) -> list[Permission]: ...
