from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container
from tarakdingdung.presentation.http.routers import build_api_router
from tarakdingdung.presentation.http.utils.errors import register_exception_handlers

_METHODS = ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
_HEADERS = ["Accept", "Authorization", "Content-Type", "Origin", "X-Requested-With"]


def build_app(container: Container, settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.app_name, version=settings.app_version,
        docs_url="/api/docs", openapi_url="/api/openapi.json",
    )
    app.state.container = container
    app.state.app_version = settings.app_version
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.http_cors_allowed_origins,
        allow_methods=_METHODS, allow_headers=_HEADERS,
    )
    register_exception_handlers(app)
    app.include_router(build_api_router())
    return app
