from fastapi import APIRouter, Depends

from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest, Session
from tarakdingdung.presentation.http.dependencies.container import get_session_usecase
from tarakdingdung.presentation.http.schemas.request import AuthLoginRequest, AuthRefreshRequest
from tarakdingdung.presentation.http.schemas.response import LoginResponse, login_response

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def auth_login(body: AuthLoginRequest,
                     session: Session = Depends(get_session_usecase)) -> LoginResponse:
    result = await session.login(LoginRequest(username=body.username, password=body.password))
    return login_response(result)


@router.post("/refresh", response_model=LoginResponse)
async def auth_refresh(body: AuthRefreshRequest,
                       session: Session = Depends(get_session_usecase)) -> LoginResponse:
    result = await session.refresh(RefreshRequest(refresh_token=body.refresh_token))
    return login_response(result)
