from decimal import Decimal

import pytest

from tarakdingdung.composition.seeder.launcher import _apply
from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.repository.backtest.repository import (
    SqlAlchemyBacktestRepository,
)
from tarakdingdung.infrastructure.repository.decision.repository import (
    SqlAlchemyDecisionRepository,
)
from tarakdingdung.infrastructure.repository.market_data.repository import (
    SqlAlchemyMarketDataRepository,
)
from tarakdingdung.infrastructure.repository.news.repository import SqlAlchemyNewsRepository
from tarakdingdung.infrastructure.repository.news_feed.repository import (
    SqlAlchemyNewsFeedRepository,
)
from tarakdingdung.infrastructure.repository.order_journal.repository import (
    SqlAlchemyOrderJournalRepository,
)
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.portfolio.repository import (
    SqlAlchemyPortfolioRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.symbol.repository import (
    SqlAlchemySymbolRepository,
)
from tarakdingdung.infrastructure.repository.universe.repository import (
    SqlAlchemyUniverseRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.repository.user_role.repository import (
    SqlAlchemyUserRoleRepository,
)
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword


def _repos(session_factory):
    return {
        "permissions": SqlAlchemyPermissionRepository(session_factory),
        "roles": SqlAlchemyRoleRepository(session_factory),
        "role_permissions": SqlAlchemyRolePermissionRepository(session_factory),
        "users": SqlAlchemyUserRepository(session_factory),
        "user_roles": SqlAlchemyUserRoleRepository(session_factory),
        "symbols": SqlAlchemySymbolRepository(session_factory),
        "universes": SqlAlchemyUniverseRepository(session_factory),
        "market_data": SqlAlchemyMarketDataRepository(session_factory),
        "news": SqlAlchemyNewsRepository(session_factory),
        "news_feeds": SqlAlchemyNewsFeedRepository(session_factory),
        "decisions": SqlAlchemyDecisionRepository(session_factory),
        "backtests": SqlAlchemyBacktestRepository(session_factory),
        "portfolio": SqlAlchemyPortfolioRepository(session_factory),
        "order_journal": SqlAlchemyOrderJournalRepository(session_factory),
    }


def _settings():
    return Settings(
        _env_file=None,
        seed_super_password="s",
        seed_admin_password="a",
        seed_user_password="u",
        engine_mode="paper",
        engine_initial_equity="10000000",
    )


async def test_seeder_is_idempotent(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    settings = _settings()

    await _apply(repos, password, settings)
    perms1, _ = await repos["permissions"].read_by_pagination(1, 100)
    roles1, _ = await repos["roles"].read_by_pagination(1, 100)
    users1, _ = await repos["users"].read_by_pagination(1, 100)

    await _apply(repos, password, settings)
    perms2, _ = await repos["permissions"].read_by_pagination(1, 100)
    roles2, _ = await repos["roles"].read_by_pagination(1, 100)
    users2, _ = await repos["users"].read_by_pagination(1, 100)

    assert len(perms1) == len(perms2)
    assert len(roles1) == len(roles2)
    assert len(users1) == len(users2)
    assert len(perms1) > 0


async def test_seeder_assigns_default_role(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    await _apply(repos, password, _settings())

    default = await repos["roles"].read_default()
    assert default is not None
    assert default.name == "user"

    user = await repos["users"].read_by_username("user")
    roles = await repos["user_roles"].read_roles_by_user(user.id)
    assert [r.name for r in roles] == ["user"]


async def test_seeder_seeds_universe_and_portfolio(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    await _apply(repos, password, _settings())

    universe = await repos["universes"].read_by_id("default")
    assert universe is not None

    from tarakdingdung.domain.models.symbol import MembershipState

    approved = await repos["universes"].read_symbols_by_state(
        "default", MembershipState.APPROVED
    )
    externals = {s.external for s in approved}
    assert "BTCIDR" in externals
    assert len(approved) >= 20

    snapshot = await repos["portfolio"].read_latest("indodax")
    assert snapshot is not None
    assert snapshot.equity == Decimal("10000000")


async def test_seeder_seeds_news_feeds(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    await _apply(repos, password, _settings())

    feeds = await repos["news_feeds"].read_enabled()
    urls = {f.url for f in feeds}
    assert "https://www.coindesk.com/arc/outboundfeeds/rss/" in urls
    assert "https://cointelegraph.com/rss" in urls
    assert len(feeds) >= 5
