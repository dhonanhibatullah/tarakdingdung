from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.application.trading.backtest.usecase import BacktestingUsecase
from tarakdingdung.application.trading.collection.usecase import MarketDataCollectionUsecase
from tarakdingdung.application.trading.engine.usecase import TradingEngineUsecase
from tarakdingdung.application.trading.history.usecase import MarketDataHistoryUsecase
from tarakdingdung.application.trading.portfolio.usecase import PortfolioSyncUsecase
from tarakdingdung.application.trading.strategy.usecase import StrategyManagementUsecase
from tarakdingdung.application.trading.validation.usecase import StrategyValidationUsecase
from tarakdingdung.composition.main.strategies import build_planner
from tarakdingdung.composition.main.infrastructure import Infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container


def build_container(infra: Infrastructure, settings: Settings | None = None) -> Container:
    log = infra.logger
    history = MarketDataHistoryUsecase(market_data=infra.market_data, logger=log)
    backtesting = BacktestingUsecase(
        strategies=infra.strategies, market_data=infra.market_data,
        backtests=infra.backtests, planner_factory=build_planner,
        cost_model=infra.cost_model, evaluator=infra.evaluator, logger=log)
    cron = settings or Settings()
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
        trading_collection=MarketDataCollectionUsecase(
            sources=infra.exchanges.markets, market_data=infra.market_data,
            strategies=infra.strategies, clock=infra.clock, logger=log),
        trading_history=history,
        trading_strategy=StrategyManagementUsecase(
            strategies=infra.strategies, logger=log),
        trading_backtest=backtesting,
        trading_validation=StrategyValidationUsecase(
            backtesting=backtesting, backtests=infra.backtests,
            overfitting=infra.overfitting, logger=log),
        trading_portfolio=PortfolioSyncUsecase(
            accounts=infra.exchanges.accounts, portfolios=infra.portfolios,
            market_data=infra.market_data, strategies=infra.strategies,
            clock=infra.clock, logger=log),
        trading_engine=TradingEngineUsecase(
            strategies=infra.strategies, history=history,
            market_data=infra.market_data, portfolios=infra.portfolios,
            journal=infra.journal, executors=infra.executors,
            planner_factory=build_planner, lock=infra.lock, clock=infra.clock,
            logger=log, interval=cron.cron_interval,
            max_age_ms=cron.cron_max_snapshot_age_seconds * 1000),
        token=infra.token,
    )
