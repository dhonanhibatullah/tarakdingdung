from decimal import Decimal

import httpx

from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.infrastructure.algorithm.backtest.fill_sim import SimpleFillSimulator
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee
from tarakdingdung.infrastructure.algorithm.metric.standard import StandardMetric
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHalt
from tarakdingdung.infrastructure.algorithm.risk.overlay import StandardRiskOverlay
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCap
from tarakdingdung.infrastructure.algorithm.risk.per_venue_cap import PerVenueCap
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import VolatilityKillSwitch
from tarakdingdung.infrastructure.llm.agents.coordinator import CoordinatorAgent
from tarakdingdung.infrastructure.llm.agents.market import MarketAgent
from tarakdingdung.infrastructure.llm.agents.news import NewsAgent
from tarakdingdung.infrastructure.llm.openai_compatible import HttpOpenAiCompatibleCompletion
from tarakdingdung.infrastructure.llm.pipeline import MultiAgentPipeline
from tarakdingdung.infrastructure.llm.validation import PydanticDecisionValidator
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogger
from tarakdingdung.infrastructure.logger.leveled.plain import PlainLeveledLogger
from tarakdingdung.infrastructure.repository.backtest.repository import (
    SqlAlchemyBacktestRepository,
)
from tarakdingdung.infrastructure.repository.database.session import create_session_factory
from tarakdingdung.infrastructure.repository.decision.repository import (
    SqlAlchemyDecisionRepository,
)
from tarakdingdung.infrastructure.repository.market_data.repository import (
    SqlAlchemyMarketDataRepository,
)
from tarakdingdung.infrastructure.repository.news.repository import SqlAlchemyNewsRepository
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
from tarakdingdung.infrastructure.scrapper.indodax.public import HttpIndodaxPublicApi
from tarakdingdung.infrastructure.scrapper.news.rss import HttpNewsSource
from tarakdingdung.infrastructure.trade.execution.live.executor import LiveExecutor
from tarakdingdung.infrastructure.trade.execution.paper.exchange import PaperExchange
from tarakdingdung.infrastructure.trade.execution.paper.executor import PaperExecutor
from tarakdingdung.infrastructure.trade.execution.reconciler import StandardReconciler
from tarakdingdung.infrastructure.trade.indodax.v2 import HttpIndodaxV2Api
from tarakdingdung.infrastructure.utility.clock.system import SystemClock
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.single_flight.memory import InMemorySingleFlight
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


def build_clock() -> Clock:
    return SystemClock()


def build_repositories(settings: Settings):
    sessions = build_session_factory(settings)
    return {
        "permissions": SqlAlchemyPermissionRepository(sessions),
        "roles": SqlAlchemyRoleRepository(sessions),
        "role_permissions": SqlAlchemyRolePermissionRepository(sessions),
        "users": SqlAlchemyUserRepository(sessions),
        "user_roles": SqlAlchemyUserRoleRepository(sessions),
        "symbols": SqlAlchemySymbolRepository(sessions),
        "universes": SqlAlchemyUniverseRepository(sessions),
        "market_data": SqlAlchemyMarketDataRepository(sessions),
        "news": SqlAlchemyNewsRepository(sessions),
        "decisions": SqlAlchemyDecisionRepository(sessions),
        "backtests": SqlAlchemyBacktestRepository(sessions),
        "portfolio": SqlAlchemyPortfolioRepository(sessions),
        "order_journal": SqlAlchemyOrderJournalRepository(sessions),
    }


def build_completion(settings: Settings):
    return HttpOpenAiCompatibleCompletion(
        httpx.AsyncClient(),
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_model,
    )


def build_market_source(settings: Settings):
    return HttpIndodaxPublicApi(httpx.AsyncClient())


def build_news_sources(settings: Settings):
    client = httpx.AsyncClient()
    return [HttpNewsSource(client, [url]) for url in settings.news_sources_list]


def build_exchange(settings: Settings):
    if settings.engine_mode == "live":
        return HttpIndodaxV2Api(
            httpx.AsyncClient(),
            settings.indodax_api_key,
            settings.indodax_secret_key,
        )
    return PaperExchange({"IDR": Decimal(settings.engine_initial_equity)})


def build_risk_overlay(settings: Settings):
    return StandardRiskOverlay(
        [
            PerPositionCap(0.3),
            PerVenueCap(0.3),
            DailyLossHalt(Decimal("500000")),
            VolatilityKillSwitch(5.0),
        ]
    )


def build_rebalancer(settings: Settings):
    return NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1000"))


def build_cost_model(settings: Settings):
    return FlatFee(Decimal("0.001"))


def build_fill_sim(settings: Settings):
    return SimpleFillSimulator(StandardMetric())


def build_decision_maker(settings: Settings, completion):
    return MultiAgentPipeline(
        MarketAgent(completion),
        NewsAgent(completion),
        CoordinatorAgent(completion),
        PydanticDecisionValidator(),
    )


def build_executor(settings: Settings, exchange, clock: Clock):
    if settings.engine_mode == "live":
        return LiveExecutor(exchange)
    return PaperExecutor(exchange, clock)


def build_single_flight(settings: Settings):
    return InMemorySingleFlight()

