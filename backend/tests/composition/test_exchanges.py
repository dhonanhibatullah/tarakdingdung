import httpx

from tarakdingdung.composition.main.exchanges import build_exchanges
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.market import Venue
from tarakdingdung.infrastructure.api.tokocrypto.v1.trade import HttpTokocryptoV1TradeApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.market import (
    HttpTokocryptoV3MarketApi,
)
from tests.fakes.trading import FakeClock
from tests.fakes.utilities import NullLogger


def test_build_exchanges_splits_tokocrypto_by_host():
    # Market data on the Binance-standard /api/v3 host (candles), signed
    # account + trading on the legacy /open/v1 host (the key only works there).
    ex = build_exchanges(httpx.AsyncClient(), Settings(),
                         clock=FakeClock(), logger=NullLogger())
    assert isinstance(ex.markets[Venue.TOKOCRYPTO]._market,
                      HttpTokocryptoV3MarketApi)
    assert isinstance(ex.accounts[Venue.TOKOCRYPTO]._trade,
                      HttpTokocryptoV1TradeApi)
    assert isinstance(ex.executors[Venue.TOKOCRYPTO]._trade,
                      HttpTokocryptoV1TradeApi)


def test_settings_expose_a_v3_base_url_default():
    assert Settings().tokocrypto_v3_base_url == "https://www.tokocrypto.site"
