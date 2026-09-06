from uuid import UUID

from fastapi import Depends, Header

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.container import get_token


def _extract_bearer(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return value or None


async def get_access_claims(
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: Token = Depends(get_token),
) -> TokenClaimsAccess:
    raw = _extract_bearer(authorization)
    if raw is None:
        raise DomainError("authorization is required", ErrorType.UNAUTHORIZED)
    return await token.validate_access(raw)


async def get_actor_id(
        claims: TokenClaimsAccess = Depends(get_access_claims)) -> UUID:
    return claims.user_id
