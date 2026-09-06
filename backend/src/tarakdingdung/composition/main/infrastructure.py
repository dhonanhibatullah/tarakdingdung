from dataclasses import dataclass
from datetime import timedelta

from tarakdingdung.composition.main.driver import Driver
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken
from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import SqlAlchemyTransactor


@dataclass(frozen=True, slots=True)
class Infrastructure:
    logger: LeveledLogger
    transactor: Transactor
    permissions: PermissionRepository
    roles: RoleRepository
    role_permissions: RolePermissionRepository
    users: UserRepository
    password: Password
    token: Token


def build_infrastructure(driver: Driver, settings: Settings) -> Infrastructure:
    db = driver.database
    return Infrastructure(
        logger=driver.logger,
        transactor=SqlAlchemyTransactor(db),
        permissions=SqlAlchemyPermissionRepository(db),
        roles=SqlAlchemyRoleRepository(db),
        role_permissions=SqlAlchemyRolePermissionRepository(db),
        users=SqlAlchemyUserRepository(db),
        password=BcryptPassword(settings.password_bcrypt_cost),
        token=JwtToken(
            access_secret=settings.token_access_secret,
            refresh_secret=settings.token_refresh_secret,
            access_ttl=timedelta(seconds=settings.token_access_ttl_seconds),
            refresh_ttl=timedelta(seconds=settings.token_refresh_ttl_seconds),
        ),
    )
