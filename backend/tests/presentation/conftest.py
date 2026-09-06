import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from fastapi import FastAPI

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.presentation.http.dependencies.container import Container
from tarakdingdung.presentation.http.routers import build_api_router
from tarakdingdung.presentation.http.utils.errors import register_exception_handlers
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, FakeToken, NullLogger


@pytest.fixture
def wiring():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    token = FakeToken()
    logger = NullLogger()
    container = Container(
        session=SessionUsecase(users=users, roles=roles, password=FakePassword(),
                               token=token, logger=logger),
        permission_management=PermissionManagementUsecase(permissions=perms, logger=logger),
        role_management=RoleManagementUsecase(roles=roles, role_permissions=rps, logger=logger),
        user_management=UserManagementUsecase(users=users, password=FakePassword(), logger=logger),
        profile_me=MeUsecase(users=users, logger=logger),
        profile_account=AccountUsecase(users=users, logger=logger),
        profile_security=SecurityUsecase(users=users, password=FakePassword(), logger=logger),
        token=token,
    )
    return container, roles, perms, rps, users


@pytest.fixture
def app(wiring):
    container = wiring[0]
    application = FastAPI()
    application.state.container = container
    application.state.app_version = "v-test"
    register_exception_handlers(application)
    application.include_router(build_api_router())
    return application


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest_asyncio.fixture
async def seeded(wiring):
    _container, roles, perms, rps, users = wiring
    rid = await roles.create(name="super", description=None, is_default=None, created_by=None)
    perm_names = ["permission:get", "permission:add", "permission:set", "permission:remove",
                  "role:get", "role:add", "role:set", "role:remove",
                  "role_permission:get", "role_permission:add", "role_permission:remove",
                  "user:get", "user:add", "user:set", "user:remove",
                  "user_permission:get", "user_password:set",
                  "profile:get", "profile:set", "profile_security:set"]
    for n in perm_names:
        pid = await perms.create(name=n, description=None, created_by=None)
        await rps.create(role_id=rid, permission_id=pid, created_by=None)
    uid = await users.create(role_id=rid, name="Super", bio=None, username="super",
                             password_hash="hash::secret12", created_by=None)
    return {"role_id": rid, "user_id": uid}
