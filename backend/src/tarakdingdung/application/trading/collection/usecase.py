from collections.abc import Callable

from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.repository.news_feed import NewsFeedRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.contracts.scrapper.market_source import MarketSource
from tarakdingdung.domain.contracts.scrapper.news_source import NewsSource
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.symbol import MembershipState
from tarakdingdung.domain.usecases.trading.collection import CollectResult, Collection


class CollectionUsecase(Collection):
    def __init__(
        self,
        universe_id: str,
        universes: UniverseRepository,
        market_data: MarketDataRepository,
        news: NewsRepository,
        market_source: MarketSource,
        news_feeds: NewsFeedRepository,
        news_source_factory: Callable[[str], NewsSource],
        clock: Clock,
        interval: str = "60",
        lookback_ms: int = 86_400_000,
    ) -> None:
        self._universe_id = universe_id
        self._universes = universes
        self._market_data = market_data
        self._news = news
        self._market_source = market_source
        self._news_feeds = news_feeds
        self._news_source_factory = news_source_factory
        self._clock = clock
        self._interval = interval
        self._lookback_ms = lookback_ms

    async def collect(self) -> CollectResult:
        failed: list[str] = []
        symbols = await self._universes.read_symbols_by_state(
            self._universe_id, MembershipState.APPROVED
        )
        now = self._clock.now_ms()
        for symbol in symbols:
            try:
                candles = await self._market_source.fetch_candles(
                    symbol, self._interval, now - self._lookback_ms, now
                )
                await self._market_data.append_candles(candles)
            except Exception:
                failed.append(f"market:{symbol.external}")

        for feed in await self._news_feeds.read_enabled():
            source = self._news_source_factory(feed.url)
            try:
                for article in await source.fetch():
                    await self._news.create(article)
            except Exception:
                failed.append(f"news:{feed.name}")

        return CollectResult(failed=failed)
