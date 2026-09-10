from dataclasses import dataclass

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.token import Token


@dataclass
class Container:
    session: SessionUsecase
    me: MeUsecase
    security: SecurityUsecase
    permission_management: PermissionManagementUsecase
    role_management: RoleManagementUsecase
    user_management: UserManagementUsecase
    token: Token
    logger: LeveledLogger
