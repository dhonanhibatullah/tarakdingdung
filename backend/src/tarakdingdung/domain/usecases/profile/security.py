from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangePasswordRequest:
    user_id: UUID
    current_password: str
    new_password: str
    updated_by: UUID | None = None


class Security(ABC):
    @abstractmethod
    async def change_password(self, request: ChangePasswordRequest) -> None: ...
