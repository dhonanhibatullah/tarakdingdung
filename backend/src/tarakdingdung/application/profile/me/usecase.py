from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.repository.user_role import UserRoleRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.me import Me, MeResult


class MeUsecase(Me):
    def __init__(
        self,
        users: UserRepository,
        user_roles: UserRoleRepository,
        roles: RoleRepository,
    ) -> None:
        self._users = users
        self._user_roles = user_roles
        self._roles = roles

    async def get(self, user_id: str) -> MeResult:
        user = await self._users.read_by_id(user_id)
        if user is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)

        assigned = await self._user_roles.read_roles_by_user(user_id)
        permissions: list[str] = []
        for role in assigned:
            for perm in await self._roles.read_permissions(role.id):
                permissions.append(perm.name)

        return MeResult(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=[r.name for r in assigned],
            permissions=sorted(set(permissions)),
        )
