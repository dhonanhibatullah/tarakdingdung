from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoginRequest:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class RefreshRequest:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class SessionResult:
    access_token: str
    refresh_token: str


class Session(ABC):
    @abstractmethod
    async def login(self, request: LoginRequest) -> SessionResult: ...

    @abstractmethod
    async def refresh(self, request: RefreshRequest) -> SessionResult: ...
