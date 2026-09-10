from fastapi import APIRouter, Depends

from tarakdingdung.domain.models.token_claims import TokenClaims
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest
from tarakdingdung.presentation.http.dependencies.auth import get_current_claims
from tarakdingdung.presentation.http.dependencies.container import get_container
from tarakdingdung.presentation.http.schemas.request import ChangePasswordBody

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me")
async def me(
    claims: TokenClaims = Depends(get_current_claims),
    container=Depends(get_container),
):
    result = await container.me.get(claims.sub)
    return {
        "id": result.id,
        "username": result.username,
        "email": result.email,
        "roles": result.roles,
        "permissions": result.permissions,
    }


@router.post("/security/password")
async def change_password(
    body: ChangePasswordBody,
    claims: TokenClaims = Depends(get_current_claims),
    container=Depends(get_container),
):
    await container.security.change_password(
        ChangePasswordRequest(
            user_id=claims.sub,
            old_password=body.old_password,
            new_password=body.new_password,
        )
    )
    return {"detail": "password changed"}
