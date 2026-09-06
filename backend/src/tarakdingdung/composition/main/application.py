from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.composition.main.infrastructure import Infrastructure
from tarakdingdung.presentation.http.dependencies.container import Container


def build_container(infra: Infrastructure) -> Container:
    log = infra.logger
    return Container(
        session=SessionUsecase(users=infra.users, roles=infra.roles,
                               password=infra.password, token=infra.token, logger=log),
        permission_management=PermissionManagementUsecase(
            permissions=infra.permissions, logger=log),
        role_management=RoleManagementUsecase(
            roles=infra.roles, role_permissions=infra.role_permissions, logger=log),
        user_management=UserManagementUsecase(
            users=infra.users, password=infra.password, logger=log),
        profile_me=MeUsecase(users=infra.users, logger=log),
        profile_account=AccountUsecase(users=infra.users, logger=log),
        profile_security=SecurityUsecase(
            users=infra.users, password=infra.password, logger=log),
        token=infra.token,
    )
