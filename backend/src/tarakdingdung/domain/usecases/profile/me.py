from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User


@dataclass(frozen=True, slots=True)
class GetProfileRequest:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class GetProfilePermissionsRequest:
    user_id: UUID


class Me(ABC):
    @abstractmethod
    async def get_profile(self, request: GetProfileRequest) -> User | None: ...

    @abstractmethod
    async def get_permissions(
        self, request: GetProfilePermissionsRequest
    ) -> list[Permission]: ...
