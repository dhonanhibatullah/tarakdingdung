from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateProfileRequest:
    user_id: UUID
    name: str | None = None
    bio: str | None = None
    username: str | None = None
    updated_by: UUID | None = None


class Account(ABC):
    @abstractmethod
    async def update_profile(self, request: UpdateProfileRequest) -> None: ...
