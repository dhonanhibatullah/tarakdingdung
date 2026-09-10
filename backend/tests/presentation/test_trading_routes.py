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
from tarakdingdung.domain.models.symbol import MembershipState, Symbol, UniverseMembership
from tarakdingdung.domain.usecases.admin.permission_management import AddPermissionRequest
from tarakdingdung.domain.usecases.admin.role_management import AddRoleRequest
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest
from tarakdingdung.domain.usecases.trading.engine import CycleResult, CycleStatus
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
from tests.fakes.trading import (
    InMemoryBacktestRepository,
    InMemoryDecisionRepository,
)


class FakeUniverse:
    def __init__(self) -> None:
        self.symbols = [Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]

    async def list(self, universe_id):
        return self.symbols

    async def propose(self, universe_id, symbol, rationale=""):
        return UniverseMembership(universe_id, symbol.id or "s1", MembershipState.PROPOSED, rationale)

    async def approve(self, universe_id, symbol_id, rationale=""):
        return UniverseMembership(universe_id, symbol_id, MembershipState.APPROVED, rationale)

    async def reject(self, universe_id, symbol_id, rationale=""):
        return UniverseMembership(universe_id, symbol_id, MembershipState.REJECTED, rationale)

    async def remove(self, universe_id, symbol_id, rationale=""):
        return UniverseMembership(universe_id, symbol_id, MembershipState.REMOVED, rationale)


class FakeEngine:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run_cycle(self):
        self.calls.append("run_cycle")
        return CycleResult(CycleStatus.EXECUTED)

    async def dry_run(self):
        self.calls.append("dry_run")
        return CycleResult(CycleStatus.EXECUTED)


PERMISSIONS = [
    "admin",
    "universe:get",
    "universe:add",
    "universe:set",
    "portfolio:get",
    "backtest:get",
    "backtest:add",
    "decision:get",
    "engine:run",
]


@pytest.fixture
async def trading_client():
    store = InMemoryStore()
    permissions = InMemoryPermissionRepository(store)
    roles = InMemoryRoleRepository(store)
    role_permissions = InMemoryRolePermissionRepository(store)
    users = InMemoryUserRepository(store)
    user_roles = InMemoryUserRoleRepository(store)
    password = BcryptPassword(cost=4)
    token = JwtToken("a" * 32, "r" * 32, 900, 86400)

    perm_mgmt = PermissionManagementUsecase(permissions)
    role_mgmt = RoleManagementUsecase(roles, permissions, role_permissions)
    user_mgmt = UserManagementUsecase(users, roles, user_roles, password)

    perm_ids = {}
    for name in PERMISSIONS:
        perm_ids[name] = (await perm_mgmt.add(AddPermissionRequest(name=name))).id
    super_role = await role_mgmt.add(AddRoleRequest(name="super"))
    for pid in perm_ids.values():
        await role_mgmt.assign_permission(super_role.id, pid)
    await user_mgmt.add(
        AddUserRequest(username="super", email="s@x.c", password="pw", role_names=["super"])
    )

    container = Container(
        session=SessionUsecase(users, roles, user_roles, password, token),
        me=MeUsecase(users, user_roles, roles),
        security=SecurityUsecase(users, password),
        permission_management=perm_mgmt,
        role_management=role_mgmt,
        user_management=user_mgmt,
        token=token,
        logger=PlainLeveledLogger(name="test"),
        universe_id="u1",
        venue="indodax",
        universe=FakeUniverse(),
        backtests=InMemoryBacktestRepository(),
        decisions=InMemoryDecisionRepository(),
        engine=FakeEngine(),
    )

    app = build_app(Settings(_env_file=None), container=container)
    yield TestClient(app), container


def _login(client):
    resp = client.post("/api/auth/login", json={"username": "super", "password": "pw"})
    return resp.json()["access_token"]


def test_list_universe(trading_client):
    client, _ = trading_client
    token = _login(client)
    resp = client.get("/api/trading/universe", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["external"] == "BTCIDR"


def test_dry_run_never_runs_live_cycle(trading_client):
    client, container = trading_client
    token = _login(client)
    resp = client.post(
        "/api/trading/engine/dry-run", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "executed"
    assert container.engine.calls == ["dry_run"]
