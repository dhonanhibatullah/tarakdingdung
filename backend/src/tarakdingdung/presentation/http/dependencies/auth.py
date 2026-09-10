from fastapi import Depends, HTTPException, Request

from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.token_claims import TokenClaims
from tarakdingdung.presentation.http.dependencies.container import get_container


def get_current_claims(
    request: Request, container=Depends(get_container)
) -> TokenClaims:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return container.token.decode(auth[7:])
    except DomainError:
        raise HTTPException(status_code=401, detail="invalid token")


def require_permission(permission: str):
    def _dep(claims: TokenClaims = Depends(get_current_claims)) -> TokenClaims:
        if permission not in claims.permissions:
            raise HTTPException(status_code=403, detail="forbidden")
        return claims

    return _dep
