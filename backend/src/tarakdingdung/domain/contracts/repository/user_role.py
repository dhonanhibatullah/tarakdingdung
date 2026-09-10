from abc import ABC, abstractmethod

from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user_role import UserRole


class UserRoleRepository(ABC):
    @abstractmethod
    async def create(self, entity: UserRole) -> UserRole: ...

    @abstractmethod
    async def read_by_user(self, user_id: str) -> list[UserRole]: ...

    @abstractmethod
    async def read_roles_by_user(self, user_id: str) -> list[Role]: ...

    @abstractmethod
    async def delete(self, user_id: str, role_id: str) -> None: ...
