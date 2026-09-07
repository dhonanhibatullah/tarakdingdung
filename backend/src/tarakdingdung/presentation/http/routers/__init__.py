from fastapi import APIRouter

from tarakdingdung.presentation.http.routers import (
    admin, auth, profile, trading, version,
)


def build_api_router() -> APIRouter:
    api = APIRouter(prefix="/api")
    api.include_router(version.router, prefix="/version")
    api.include_router(auth.router)
    api.include_router(admin.router)
    api.include_router(profile.router)
    api.include_router(trading.router)
    return api
