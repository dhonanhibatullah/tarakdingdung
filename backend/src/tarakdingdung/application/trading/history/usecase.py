from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.market import Coverage, MarketSnapshot
from tarakdingdung.domain.usecases.trading.history import (
    MarketDataHistory, ReadCandlesRequest, ReadCandlesResult, ReadCoverageRequest,
    ReadSnapshotRequest,
)


class MarketDataHistoryUsecase(MarketDataHistory):
    _TAG = "trading/history"

    def __init__(self, *, market_data: MarketDataRepository,
                 logger: LeveledLogger) -> None:
        self._market_data = market_data
        self._logger = logger

    async def read_candles(self, request: ReadCandlesRequest) -> ReadCandlesResult:
        try:
            candles = await self._market_data.read_candles(
                symbol=request.symbol, interval=request.interval,
                window=request.window, limit=request.limit)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ReadCandles", "failed to read candles",
                                     {"err": err, "symbol": str(request.symbol)})
            raise
        return ReadCandlesResult(symbol=request.symbol, interval=request.interval,
                                 candles=candles)

    async def read_snapshot(self, request: ReadSnapshotRequest) -> MarketSnapshot:
        try:
            return await self._market_data.read_snapshot(
                symbols=request.symbols, as_of=request.as_of,
                interval=request.interval, lookback=request.lookback,
                max_age=request.max_age_ms)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ReadSnapshot", "failed to read snapshot",
                                     {"err": err, "as_of": request.as_of})
            raise

    async def read_coverage(self, request: ReadCoverageRequest) -> Coverage:
        try:
            return await self._market_data.read_coverage(
                symbol=request.symbol, interval=request.interval, window=request.window)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ReadCoverage", "failed to read coverage",
                                     {"err": err, "symbol": str(request.symbol)})
            raise
