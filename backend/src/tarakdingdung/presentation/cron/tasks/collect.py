from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.usecases.trading.collection import (
    CollectRequest, MarketDataCollection,
)

TAG = "cron/collect"


async def collect_market_data(*, collection: MarketDataCollection,
                              logger: LeveledLogger, interval: str) -> None:
    """Poll every venue for the enabled strategies' symbols.

    Partial failure is logged as a warning, never raised: the collector already
    returns what it could not fetch, and turning that into an exception would
    stop the scheduler over a single unreachable venue.
    """
    result = await collection.collect(CollectRequest(interval=interval))
    if result.failed:
        await logger.warn(TAG, "collection incomplete", {
            "collected": len(result.collected), "failed": len(result.failed),
            "reasons": sorted({f.reason for f in result.failed})})
        return
    await logger.info(TAG, "collected market data", {
        "collected": len(result.collected), "candles": result.candles_written})
