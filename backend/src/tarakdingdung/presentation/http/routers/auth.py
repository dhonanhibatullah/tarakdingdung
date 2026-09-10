from fastapi import APIRouter, Depends

from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest
from tarakdingdung.presentation.http.dependencies.container import get_container
from tarakdingdung.presentation.http.schemas.request import LoginBody, RefreshBody

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginBody, container=Depends(get_container)):
    result = await container.session.login(
        LoginRequest(username=body.username, password=body.password)
    )
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
    }


@router.post("/refresh")
async def refresh(body: RefreshBody, container=Depends(get_container)):
    result = await container.session.refresh(
        RefreshRequest(refresh_token=body.refresh_token)
    )
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
    }
