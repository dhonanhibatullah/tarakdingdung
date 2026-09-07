import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container
from tarakdingdung.presentation.http.routers import build_api_router
from tarakdingdung.presentation.http.utils.errors import register_exception_handlers

_METHODS = ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
_HEADERS = ["Accept", "Authorization", "Content-Type", "Origin", "X-Requested-With"]


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI):
    """Start whatever background work the app owns, then release its drivers.

    Startup hooks are registered on ``app.state.on_startup`` by the composition
    root rather than imported here, so the presentation layer does not need to
    know that a cron exists.
    """
    startup = getattr(app.state, "on_startup", None)
    shutdown = await startup() if startup is not None else None
    try:
        yield
    finally:
        if shutdown is not None:
            await shutdown()
        driver = getattr(app.state, "driver", None)
        if driver is not None:
            await driver.database.dispose()
            await driver.http.aclose()


def build_app(container: Container, settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.app_name, version=settings.app_version,
        docs_url="/api/docs", openapi_url="/api/openapi.json",
        lifespan=_lifespan,
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
