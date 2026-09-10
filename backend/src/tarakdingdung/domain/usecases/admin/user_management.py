from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tarakdingdung.domain.models.user import User


@dataclass(frozen=True, slots=True)
class AddUserRequest:
    username: str
    email: str
    password: str
    role_names: list[str] = field(default_factory=list)


class UserManagement(ABC):
    @abstractmethod
    async def add(self, request: AddUserRequest) -> User: ...

    @abstractmethod
    async def list(self, page: int, per_page: int) -> tuple[list[User], int]: ...

    @abstractmethod
    async def deactivate(self, user_id: str) -> User: ...
