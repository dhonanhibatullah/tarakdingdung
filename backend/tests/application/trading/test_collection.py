from decimal import Decimal

from tarakdingdung.application.trading.collection.usecase import CollectionUsecase
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.news import NewsArticle
from tarakdingdung.domain.models.symbol import Symbol
from tests.fakes.trading import (
    InMemoryMarketDataRepository,
    InMemoryNewsRepository,
    InMemoryUniverseRepository,
)


class FakeClock:
    def now_ms(self) -> int:
        return 1_700_000_000_000


class FakeMarketSource:
    def __init__(self, fail=False) -> None:
        self.fail = fail

    async def fetch_candles(self, symbol, interval, from_ms, to_ms):
        if self.fail:
            raise RuntimeError("down")
        return [
            Candle(
                symbol_id=symbol.id,
                open_time_ms=from_ms,
                open=Decimal("1"),
                high=Decimal("1"),
                low=Decimal("1"),
                close=Decimal("1"),
                volume=Decimal("1"),
            )
        ]

    async def fetch_ticker(self, symbol):
        raise NotImplementedError


class FakeNewsSource:
    def __init__(self, fail=False) -> None:
        self.fail = fail

    async def fetch(self):
        if self.fail:
            raise RuntimeError("down")
        return [
            NewsArticle(
                id="", source="s", url="u", title="t", published_ms=1, raw_text="x"
            )
        ]


def _usecase(market_data, news, universe, market_source, news_sources):
    return CollectionUsecase(
        universe_id="u1",
        universes=universe,
        market_data=market_data,
        news=news,
        market_source=market_source,
        news_sources=news_sources,
        clock=FakeClock(),
    )


async def test_collect_candles_and_news():
    universe = InMemoryUniverseRepository(
        approved_symbols=[Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]
    )
    market_data = InMemoryMarketDataRepository()
    news = InMemoryNewsRepository()

    usecase = _usecase(
        market_data, news, universe, FakeMarketSource(), [FakeNewsSource()]
    )
    result = await usecase.collect()

    assert result.failed == []
    assert len(market_data.candles) == 1
    assert len(news.articles) == 1


async def test_collect_tolerates_partial_failure():
    universe = InMemoryUniverseRepository(
        approved_symbols=[Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]
    )
    market_data = InMemoryMarketDataRepository()
    news = InMemoryNewsRepository()

    usecase = _usecase(
        market_data, news, universe, FakeMarketSource(fail=True), [FakeNewsSource(fail=True)]
    )
    result = await usecase.collect()

    assert len(result.failed) == 2
    assert market_data.candles == []
    assert news.articles == []
