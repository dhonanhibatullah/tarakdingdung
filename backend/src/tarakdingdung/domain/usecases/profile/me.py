from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MeResult:
    id: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]


class Me(ABC):
    @abstractmethod
    async def get(self, user_id: str) -> MeResult: ...
