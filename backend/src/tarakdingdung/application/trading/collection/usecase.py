from collections.abc import Mapping

from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.execution import CollectionFailure
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.usecases.trading.collection import (
    CollectRequest, CollectResult, MarketDataCollection,
)


class MarketDataCollectionUsecase(MarketDataCollection):
    """Polls every venue for the symbols the enabled strategies care about.

    Every venue call is guarded individually. A symbol that fails is recorded
    and the pass continues, because aborting would leave the *other* venue's
    history gapped for the same interval — and a gap is permanent in a way a
    failed poll is not.
    """

    _TAG = "trading/collection"

    def __init__(self, *, sources: Mapping[Venue, MarketDataSource],
                 market_data: MarketDataRepository, strategies: StrategyRepository,
                 clock: Clock, logger: LeveledLogger,
                 candle_limit: int = 200, book_limit: int = 50) -> None:
        self._sources = sources
        self._market_data = market_data
        self._strategies = strategies
        self._clock = clock
        self._logger = logger
        self._candle_limit = candle_limit
        self._book_limit = book_limit

    async def collect(self, request: CollectRequest) -> CollectResult:
        now = await self._clock.now_ms()
        symbols = request.symbols or await self._universe()

        collected: list[Symbol] = []
        failures: list[CollectionFailure] = []
        written = 0

        await self._collect_rules(failures)
        for symbol in symbols:
            source = self._sources.get(symbol.venue)
            if source is None:
                failures.append(CollectionFailure(
                    venue=symbol.venue, symbol=symbol, reason="no source configured"))
                continue
            try:
                written += await self._collect_symbol(source, symbol, request)
            except DomainError as err:
                await self._logger.warn(f"{self._TAG}/Collect", "failed to collect symbol",
                                        {"err": err, "symbol": str(symbol)})
                failures.append(CollectionFailure(
                    venue=symbol.venue, symbol=symbol, reason=err.message))
                continue
            collected.append(symbol)

        return CollectResult(timestamp=now, collected=tuple(collected),
                             candles_written=written, failed=tuple(failures))

    async def _universe(self) -> tuple[Symbol, ...]:
        enabled = await self._strategies.read_enabled()
        seen = {symbol for config in enabled for symbol in config.universe}
        return tuple(sorted(seen, key=lambda s: (s.venue, s.base, s.quote)))

    async def _collect_symbol(self, source: MarketDataSource, symbol: Symbol,
                              request: CollectRequest) -> int:
        candles = await source.fetch_candles(
            symbol=symbol, interval=request.interval, limit=self._candle_limit)
        written = await self._market_data.write_candles(
            symbol=symbol, interval=request.interval, candles=candles)

        price = await source.fetch_price(symbol=symbol)
        stamped = candles[-1].open_time if candles else 0
        await self._market_data.write_price(
            symbol=symbol, timestamp=stamped, price=price)

        if request.include_books:
            await self._market_data.write_book(
                await source.fetch_book(symbol=symbol, limit=self._book_limit))
        return written

    async def _collect_rules(self, failures: list[CollectionFailure]) -> None:
        # Rules change rarely but must be stored, because the engine reads them
        # from storage rather than calling a venue mid-cycle.
        for venue, source in self._sources.items():
            try:
                await self._market_data.write_rules(await source.fetch_rules())
            except DomainError as err:
                await self._logger.warn(f"{self._TAG}/Collect", "failed to collect rules",
                                        {"err": err, "venue": venue})
                failures.append(CollectionFailure(
                    venue=venue, symbol=None, reason=err.message))
