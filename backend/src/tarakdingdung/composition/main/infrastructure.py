from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from tarakdingdung.composition.main.driver import Driver
from tarakdingdung.config.settings import Settings
from tarakdingdung.composition.main.exchanges import Exchanges, build_exchanges
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.infrastructure.algorithm.cost.depth_walk import DepthWalkCostModel
from tarakdingdung.infrastructure.algorithm.metric.standard import (
    StandardPerformanceEvaluator,
)
from tarakdingdung.infrastructure.algorithm.validation.combinatorial import (
    CombinatorialOverfittingTest,
)
from tarakdingdung.infrastructure.execution.live.router import RoutingExecutor
from tarakdingdung.infrastructure.execution.paper.executor import PaperExecutor
from tarakdingdung.infrastructure.repository.backtest.repository import (
    SqlAlchemyBacktestRepository,
)
from tarakdingdung.infrastructure.repository.market_data.repository import (
    SqlAlchemyMarketDataRepository,
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
from tarakdingdung.infrastructure.repository.strategy.repository import (
    SqlAlchemyStrategyRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.utility.clock.system import SystemClock
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.single_flight.postgres import PostgresSingleFlight
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
    clock: Clock
    lock: SingleFlight
    market_data: MarketDataRepository
    strategies: StrategyRepository
    backtests: BacktestRepository
    portfolios: PortfolioRepository
    journal: OrderJournalRepository
    exchanges: Exchanges
    executors: dict[TradingMode, Executor]
    cost_model: DepthWalkCostModel
    evaluator: StandardPerformanceEvaluator
    overfitting: CombinatorialOverfittingTest


def build_infrastructure(driver: Driver, settings: Settings) -> Infrastructure:
    db = driver.database
    clock = SystemClock()
    market_data = SqlAlchemyMarketDataRepository(db)
    exchanges = build_exchanges(driver.http, settings, clock=clock,
                                logger=driver.logger)
    # A depth-walking cost model in both places, so paper fills are priced the
    # way the backtester prices them and the two stay comparable.
    cost_model = DepthWalkCostModel(fee_rate=Decimal("0.002"))
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
        clock=clock,
        lock=PostgresSingleFlight(db),
        market_data=market_data,
        strategies=SqlAlchemyStrategyRepository(db),
        backtests=SqlAlchemyBacktestRepository(db),
        portfolios=SqlAlchemyPortfolioRepository(db),
        journal=SqlAlchemyOrderJournalRepository(db),
        exchanges=exchanges,
        executors={
            TradingMode.PAPER: PaperExecutor(market_data=market_data,
                                             cost_model=cost_model, clock=clock),
            TradingMode.LIVE: RoutingExecutor(exchanges.executors),
        },
        cost_model=cost_model,
        evaluator=StandardPerformanceEvaluator(),
        overfitting=CombinatorialOverfittingTest(),
    )
