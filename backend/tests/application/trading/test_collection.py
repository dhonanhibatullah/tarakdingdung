from decimal import Decimal

from tarakdingdung.application.trading.collection.usecase import CollectionUsecase
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.news import NewsArticle, NewsFeed
from tarakdingdung.domain.models.symbol import Symbol
from tests.fakes.trading import (
    InMemoryMarketDataRepository,
    InMemoryNewsFeedRepository,
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
    def __init__(self, url, fail=False) -> None:
        self.url = url
        self.fail = fail

    async def fetch(self):
        if self.fail:
            raise RuntimeError("down")
        return [
            NewsArticle(
                id="", source=self.url, url="u", title="t", published_ms=1, raw_text="x"
            )
        ]


def _usecase(market_data, news, universe, market_source, news_feeds, news_factory=None):
    if news_factory is None:
        news_factory = lambda url: FakeNewsSource(url)
    return CollectionUsecase(
        universe_id="u1",
        universes=universe,
        market_data=market_data,
        news=news,
        market_source=market_source,
        news_feeds=news_feeds,
        news_source_factory=news_factory,
        clock=FakeClock(),
    )


async def test_collect_candles_and_news():
    universe = InMemoryUniverseRepository(
        approved_symbols=[Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]
    )
    market_data = InMemoryMarketDataRepository()
    news = InMemoryNewsRepository()
    news_feeds = InMemoryNewsFeedRepository([NewsFeed(id="f1", name="CoinDesk", url="https://example.com/rss")])

    usecase = _usecase(market_data, news, universe, FakeMarketSource(), news_feeds)
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
    news_feeds = InMemoryNewsFeedRepository([NewsFeed(id="f1", name="Down", url="https://example.com/rss")])

    usecase = _usecase(
        market_data,
        news,
        universe,
        FakeMarketSource(fail=True),
        news_feeds,
        news_factory=lambda url: FakeNewsSource(url, fail=True),
    )
    result = await usecase.collect()

    assert len(result.failed) == 2
    assert market_data.candles == []
    assert news.articles == []


async def test_collect_skips_disabled_feeds():
    universe = InMemoryUniverseRepository(approved_symbols=[])
    market_data = InMemoryMarketDataRepository()
    news = InMemoryNewsRepository()
    news_feeds = InMemoryNewsFeedRepository(
        [NewsFeed(id="f1", name="Disabled", url="https://example.com/rss", enabled=False)]
    )

    usecase = _usecase(market_data, news, universe, FakeMarketSource(), news_feeds)
    result = await usecase.collect()

    assert result.failed == []
    assert news.articles == []
