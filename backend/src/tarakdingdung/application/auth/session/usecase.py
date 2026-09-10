from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.repository.user_role import UserRoleRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaims
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.auth.session import (
    LoginRequest,
    RefreshRequest,
    Session,
    SessionResult,
)


class SessionUsecase(Session):
    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        user_roles: UserRoleRepository,
        password: Password,
        token: Token,
    ) -> None:
        self._users = users
        self._roles = roles
        self._user_roles = user_roles
        self._password = password
        self._token = token

    async def login(self, request: LoginRequest) -> SessionResult:
        user = await self._users.read_by_username(request.username)
        if user is None or user.is_deleted:
            raise DomainError("invalid credentials", ErrorType.UNAUTHORIZED)
        if not self._password.verify(request.password, user.password_hash):
            raise DomainError("invalid credentials", ErrorType.UNAUTHORIZED)
        if not user.is_active:
            raise DomainError("account is inactive", ErrorType.FORBIDDEN)
        return await self._issue_tokens(user)

    async def refresh(self, request: RefreshRequest) -> SessionResult:
        claims = self._token.decode_refresh(request.refresh_token)
        user = await self._users.read_by_id(claims.sub)
        if user is None or user.is_deleted or not user.is_active:
            raise DomainError("invalid token", ErrorType.UNAUTHORIZED)
        return await self._issue_tokens(user)

    async def _issue_tokens(self, user: User) -> SessionResult:
        roles = await self._user_roles.read_roles_by_user(user.id)
        permissions: list[str] = []
        for role in roles:
            for perm in await self._roles.read_permissions(role.id):
                permissions.append(perm.name)
        permissions = sorted(set(permissions))

        claims = TokenClaims(
            sub=user.id,
            username=user.username,
            roles=[r.name for r in roles],
            permissions=permissions,
        )
        return SessionResult(
            access_token=self._token.encode_access(claims),
            refresh_token=self._token.encode_refresh(claims),
        )
