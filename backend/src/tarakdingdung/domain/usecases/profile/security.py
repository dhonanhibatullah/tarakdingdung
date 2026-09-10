from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChangePasswordRequest:
    user_id: str
    old_password: str
    new_password: str


class Security(ABC):
    @abstractmethod
    async def change_password(self, request: ChangePasswordRequest) -> None: ...
