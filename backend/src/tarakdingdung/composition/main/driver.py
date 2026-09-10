from fastapi import FastAPI

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.composition.main.application import Container
from tarakdingdung.composition.main import infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.routers import admin, auth, profile, trading, version
from tarakdingdung.presentation.http.utils.errors import register_error_handlers


def build_container(settings: Settings) -> Container:
    logger = infrastructure.build_logger(settings)
    repos = infrastructure.build_repositories(settings)
    password = infrastructure.build_password(settings)
    token = infrastructure.build_token(settings)

    return Container(
        session=SessionUsecase(
            repos["users"], repos["roles"], repos["user_roles"], password, token
        ),
        me=MeUsecase(repos["users"], repos["user_roles"], repos["roles"]),
        security=SecurityUsecase(repos["users"], password),
        permission_management=PermissionManagementUsecase(repos["permissions"]),
        role_management=RoleManagementUsecase(
            repos["roles"], repos["permissions"], repos["role_permissions"]
        ),
        user_management=UserManagementUsecase(
            repos["users"], repos["roles"], repos["user_roles"], password
        ),
        token=token,
        logger=logger,
    )


def build_app(
    settings: Settings | None = None, container: Container | None = None
) -> FastAPI:
    settings = settings or Settings()
    if container is None:
        container = build_container(settings)

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.state.settings = settings
    app.state.container = container

    register_error_handlers(app)
    app.include_router(version.router)
    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(admin.router)
    app.include_router(trading.router)
    return app
