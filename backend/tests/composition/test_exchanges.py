import httpx

from tarakdingdung.composition.main.exchanges import build_exchanges
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.market import Venue
from tarakdingdung.infrastructure.api.tokocrypto.v3.market import (
    HttpTokocryptoV3MarketApi,
)
from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import (
    HttpTokocryptoV3TradeApi,
)
from tests.fakes.trading import FakeClock
from tests.fakes.utilities import NullLogger


def test_build_exchanges_wires_tokocrypto_onto_v3():
    ex = build_exchanges(httpx.AsyncClient(), Settings(),
                         clock=FakeClock(), logger=NullLogger())
    assert isinstance(ex.markets[Venue.TOKOCRYPTO]._market,
                      HttpTokocryptoV3MarketApi)
    assert isinstance(ex.accounts[Venue.TOKOCRYPTO]._trade,
                      HttpTokocryptoV3TradeApi)
    assert isinstance(ex.executors[Venue.TOKOCRYPTO]._trade,
                      HttpTokocryptoV3TradeApi)


def test_settings_expose_a_v3_base_url_default():
    assert Settings().tokocrypto_v3_base_url == "https://www.tokocrypto.site"
