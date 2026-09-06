from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.auth.session import (
    LoginRequest, LoginResult, RefreshRequest, Session,
)


class SessionUsecase(Session):
    _TAG = "auth/session"

    def __init__(self, *, users: UserRepository, roles: RoleRepository,
                 password: Password, token: Token, logger: LeveledLogger) -> None:
        self._users = users
        self._roles = roles
        self._password = password
        self._token = token
        self._logger = logger

    async def login(self, request: LoginRequest) -> LoginResult:
        user = await self._users.read_by_username(request.username)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/Login", "failed to read user", {"err": err})
            raise err
        try:
            await self._password.compare(user.password_hash, request.password)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Login", "failed to compare password",
                                     {"err": err, "user_id": user.id})
            raise
        return await self._build_login_result(user, "Login")

    async def refresh(self, request: RefreshRequest) -> LoginResult:
        try:
            claims: TokenClaimsRefresh = await self._token.validate_refresh(request.refresh_token)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Refresh", "failed to validate refresh token",
                                     {"err": err})
            raise
        user = await self._users.read_by_id(claims.user_id)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/Refresh", "failed to read user",
                                     {"err": err, "user_id": claims.user_id})
            raise err
        return await self._build_login_result(user, "Refresh")

    async def _build_login_result(self, user: User, method: str) -> LoginResult:
        role = await self._roles.read_by_id(user.role_id)
        if role is None:
            err = DomainError("role not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/{method}", "failed to read user role",
                                     {"err": err, "user_id": user.id, "role_id": user.role_id})
            raise err
        permissions = await self._users.read_permissions(user.id)
        access = await self._token.generate_access(TokenClaimsAccess(
            user_id=user.id, name=user.name, username=user.username, role=role.name,
            permissions=tuple(p.name for p in permissions)))
        refresh = await self._token.generate_refresh(TokenClaimsRefresh(user_id=user.id))
        return LoginResult(user=user, role=role, permissions=tuple(permissions),
                           access_token=access, refresh_token=refresh)
