"""Venue clients, wired per exchange.

Kept apart from ``infrastructure.py`` because this is where credentials meet
network clients, and it is worth being able to read the whole trust boundary in
one file.
"""

from dataclasses import dataclass

import httpx

from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.market import Venue
from tarakdingdung.infrastructure.api.indodax.v1.public import HttpIndodaxV1PublicApi
from tarakdingdung.infrastructure.api.indodax.v2.trade import HttpIndodaxV2TradeApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.market import HttpTokocryptoV1MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v1.trade import HttpTokocryptoV1TradeApi
from tarakdingdung.infrastructure.execution.live.indodax import IndodaxLiveExecutor
from tarakdingdung.infrastructure.execution.live.tokocrypto import TokocryptoLiveExecutor
from tarakdingdung.infrastructure.venue.indodax.account import IndodaxAccountSource
from tarakdingdung.infrastructure.venue.indodax.market import IndodaxMarketDataSource
from tarakdingdung.infrastructure.venue.tokocrypto.account import TokocryptoAccountSource
from tarakdingdung.infrastructure.venue.tokocrypto.market import TokocryptoMarketDataSource


@dataclass(frozen=True, slots=True)
class Exchanges:
    markets: dict[Venue, MarketDataSource]
    accounts: dict[Venue, AccountSource]
    executors: dict[Venue, Executor]


def build_exchanges(http: httpx.AsyncClient, settings: Settings, *,
                    clock: Clock, logger: LeveledLogger) -> Exchanges:
    indodax_public = HttpIndodaxV1PublicApi(http)
    indodax_trade = HttpIndodaxV2TradeApi(
        http, api_key=settings.indodax_v2_api_key,
        secret_key=settings.indodax_v2_secret_key)
    tokocrypto_market = HttpTokocryptoV1MarketApi(http)
    tokocrypto_trade = HttpTokocryptoV1TradeApi(
        http, api_key=settings.tokocrypto_api_key,
        secret_key=settings.tokocrypto_secret_key)

    return Exchanges(
        markets={
            Venue.INDODAX: IndodaxMarketDataSource(public=indodax_public, clock=clock),
            Venue.TOKOCRYPTO: TokocryptoMarketDataSource(
                market=tokocrypto_market, clock=clock),
        },
        accounts={
            Venue.INDODAX: IndodaxAccountSource(trade=indodax_trade),
            Venue.TOKOCRYPTO: TokocryptoAccountSource(trade=tokocrypto_trade),
        },
        executors={
            Venue.INDODAX: IndodaxLiveExecutor(trade=indodax_trade, logger=logger),
            Venue.TOKOCRYPTO: TokocryptoLiveExecutor(
                trade=tokocrypto_trade, logger=logger),
        },
    )
