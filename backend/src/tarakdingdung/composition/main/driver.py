from decimal import Decimal

from fastapi import FastAPI

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.application.trading.backtest.usecase import BacktestUsecase
from tarakdingdung.application.trading.collection.usecase import CollectionUsecase
from tarakdingdung.application.trading.engine.usecase import TradingEngineUsecase
from tarakdingdung.application.trading.portfolio.usecase import PortfolioUsecase
from tarakdingdung.application.trading.snapshot.usecase import SnapshotUsecase
from tarakdingdung.application.trading.universe.usecase import UniverseUsecase
from tarakdingdung.composition.main.application import Container
from tarakdingdung.composition.main import infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.trade.execution.reconciler import StandardReconciler
from tarakdingdung.presentation.http.routers import admin, auth, profile, trading, version
from tarakdingdung.presentation.http.utils.errors import register_error_handlers


def build_container(settings: Settings) -> Container:
    logger = infrastructure.build_logger(settings)
    repos = infrastructure.build_repositories(settings)
    password = infrastructure.build_password(settings)
    token = infrastructure.build_token(settings)
    clock = infrastructure.build_clock()

    exchange = infrastructure.build_exchange(settings)
    completion = infrastructure.build_completion(settings)
    decision_maker = infrastructure.build_decision_maker(settings, completion)
    risk_overlay = infrastructure.build_risk_overlay(settings)
    rebalancer = infrastructure.build_rebalancer(settings)
    cost_model = infrastructure.build_cost_model(settings)
    fill_sim = infrastructure.build_fill_sim(settings)
    market_source = infrastructure.build_market_source(settings)
    news_sources = infrastructure.build_news_sources(settings)
    executor = infrastructure.build_executor(settings, exchange, clock)
    reconciler = StandardReconciler(exchange)
    single_flight = infrastructure.build_single_flight(settings)

    universe_id = settings.universe_id
    venue = settings.engine_venue

    universe = UniverseUsecase(repos["universes"], repos["symbols"])
    portfolio = PortfolioUsecase(repos["portfolio"])
    backtest = BacktestUsecase(
        repos["decisions"],
        repos["market_data"],
        repos["backtests"],
        rebalancer,
        fill_sim,
        cost_model,
        Decimal(settings.engine_initial_equity),
    )
    snapshot = SnapshotUsecase(
        exchange,
        universe_id,
        venue,
        repos["universes"],
        repos["market_data"],
        repos["portfolio"],
        clock,
    )
    collection = CollectionUsecase(
        universe_id,
        repos["universes"],
        repos["market_data"],
        repos["news"],
        market_source,
        news_sources,
        clock,
    )
    engine = TradingEngineUsecase(
        enabled=settings.engine_enabled,
        universe_id=universe_id,
        venue=venue,
        single_flight=single_flight,
        universes=repos["universes"],
        order_journal=repos["order_journal"],
        reconciler=reconciler,
        portfolio=repos["portfolio"],
        market_data=repos["market_data"],
        news=repos["news"],
        decision_maker=decision_maker,
        decisions=repos["decisions"],
        risk_overlay=risk_overlay,
        rebalancer=rebalancer,
        executor=executor,
        clock=clock,
    )

    return Container(
        session=SessionUsecase(
            repos["users"], repos["roles"], repos["user_roles"], password, token
        ),
        me=MeUsecase(repos["users"], repos["user_roles"], repos["roles"]),
        security=SecurityUsecase(repos["users"], password),
        permission_management=PermissionManagementUsecase(repos["permissions"]),
        role_management=RoleManagementUsecase(
            repos["roles"], repos["permissions"], repos["role_permissions"]
        ),
        user_management=UserManagementUsecase(
            repos["users"], repos["roles"], repos["user_roles"], password
        ),
        token=token,
        logger=logger,
        universe_id=universe_id,
        venue=venue,
        universe=universe,
        portfolio=portfolio,
        backtest=backtest,
        snapshot=snapshot,
        collection=collection,
        engine=engine,
        backtests=repos["backtests"],
        decisions=repos["decisions"],
    )


def build_app(
    settings: Settings | None = None, container: Container | None = None
) -> FastAPI:
    settings = settings or Settings()
    if container is None:
        container = build_container(settings)

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.state.settings = settings
    app.state.container = container

    register_error_handlers(app)
    app.include_router(version.router)
    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(admin.router)
    app.include_router(trading.router)
    return app
