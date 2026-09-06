from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user import User


@dataclass(frozen=True, slots=True)
class LoginRequest:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class RefreshRequest:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    role: Role
    permissions: tuple[Permission, ...]
    access_token: str
    refresh_token: str


class Session(ABC):
    @abstractmethod
    async def login(self, request: LoginRequest) -> LoginResult: ...

    @abstractmethod
    async def refresh(self, request: RefreshRequest) -> LoginResult: ...
