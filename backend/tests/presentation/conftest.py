import pytest
from fastapi.testclient import TestClient

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.composition.main.application import Container
from tarakdingdung.composition.main.driver import build_app
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.usecases.admin.permission_management import AddPermissionRequest
from tarakdingdung.domain.usecases.admin.role_management import AddRoleRequest
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest
from tarakdingdung.infrastructure.logger.leveled.plain import PlainLeveledLogger
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken
from tests.fakes.repositories import (
    InMemoryPermissionRepository,
    InMemoryRolePermissionRepository,
    InMemoryRoleRepository,
    InMemoryStore,
    InMemoryUserRepository,
    InMemoryUserRoleRepository,
)


@pytest.fixture
async def client():
    store = InMemoryStore()
    permissions = InMemoryPermissionRepository(store)
    roles = InMemoryRoleRepository(store)
    role_permissions = InMemoryRolePermissionRepository(store)
    users = InMemoryUserRepository(store)
    user_roles = InMemoryUserRoleRepository(store)
    password = BcryptPassword(cost=4)
    token = JwtToken("a" * 32, "r" * 32, 900, 86400)

    container = Container(
        session=SessionUsecase(users, roles, user_roles, password, token),
        me=MeUsecase(users, user_roles, roles),
        security=SecurityUsecase(users, password),
        permission_management=PermissionManagementUsecase(permissions),
        role_management=RoleManagementUsecase(roles, permissions, role_permissions),
        user_management=UserManagementUsecase(users, roles, user_roles, password),
        token=token,
        logger=PlainLeveledLogger(name="test"),
    )

    admin_perm = await container.permission_management.add(
        AddPermissionRequest(name="admin")
    )
    super_role = await container.role_management.add(AddRoleRequest(name="super"))
    await container.role_management.assign_permission(super_role.id, admin_perm.id)
    await container.user_management.add(
        AddUserRequest(
            username="super", email="s@x.c", password="pw", role_names=["super"]
        )
    )

    settings = Settings(_env_file=None)
    app = build_app(settings, container=container)
    yield TestClient(app)
