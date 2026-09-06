from collections.abc import Callable

from fastapi import Depends

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.auth import get_access_claims


def require(*required: str) -> Callable:
    async def _dependency(
            claims: TokenClaimsAccess = Depends(get_access_claims)) -> None:
        if not set(required).issubset(set(claims.permissions)):
            raise DomainError("you do not have permission to perform this action",
                              ErrorType.FORBIDDEN)

    return _dependency
