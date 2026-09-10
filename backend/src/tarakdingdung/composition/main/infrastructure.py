from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogger
from tarakdingdung.infrastructure.logger.leveled.plain import PlainLeveledLogger
from tarakdingdung.infrastructure.repository.database.session import create_session_factory
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.repository.user_role.repository import (
    SqlAlchemyUserRoleRepository,
)
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken


def build_logger(settings: Settings) -> LeveledLogger:
    if settings.logger_format == "json":
        return JsonLeveledLogger(level=settings.logger_level)
    return PlainLeveledLogger(level=settings.logger_level)


def build_session_factory(settings: Settings):
    return create_session_factory(settings.postgres_dsn, settings.postgres_pool_size)


def build_password(settings: Settings) -> Password:
    return BcryptPassword(settings.password_bcrypt_cost)


def build_token(settings: Settings) -> Token:
    return JwtToken(
        settings.token_access_secret,
        settings.token_refresh_secret,
        settings.token_access_ttl_seconds,
        settings.token_refresh_ttl_seconds,
    )


def build_repositories(settings: Settings):
    sessions = build_session_factory(settings)
    return {
        "permissions": SqlAlchemyPermissionRepository(sessions),
        "roles": SqlAlchemyRoleRepository(sessions),
        "role_permissions": SqlAlchemyRolePermissionRepository(sessions),
        "users": SqlAlchemyUserRepository(sessions),
        "user_roles": SqlAlchemyUserRoleRepository(sessions),
    }
