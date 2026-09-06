from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


class FakePassword(Password):
    async def hash(self, password: str) -> str:
        return f"hash::{password}"

    async def compare(self, stored_hash: str, password: str) -> None:
        if stored_hash != f"hash::{password}":
            raise DomainError("password does not match", ErrorType.UNAUTHORIZED)


class FakeToken(Token):
    def __init__(self) -> None:
        self.last_access: TokenClaimsAccess | None = None

    async def generate_access(self, claims: TokenClaimsAccess) -> str:
        self.last_access = claims
        return f"access::{claims.user_id}"

    async def validate_access(self, token: str) -> TokenClaimsAccess:
        if self.last_access and token == f"access::{self.last_access.user_id}":
            return self.last_access
        raise DomainError("token is invalid", ErrorType.TOKEN_INVALID)

    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str:
        return f"refresh::{claims.user_id}"

    async def validate_refresh(self, token: str) -> TokenClaimsRefresh:
        if not token.startswith("refresh::"):
            raise DomainError("token is invalid", ErrorType.TOKEN_INVALID)
        import uuid
        return TokenClaimsRefresh(user_id=uuid.UUID(token.removeprefix("refresh::")))


class NullLogger(LeveledLogger):
    async def error(self, tag, message, meta) -> None: ...
    async def warn(self, tag, message, meta) -> None: ...
    async def info(self, tag, message, meta) -> None: ...
    async def debug(self, tag, message, meta) -> None: ...
