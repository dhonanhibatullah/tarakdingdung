from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.usecases.trading.portfolio import PortfolioSync, SyncRequest

TAG = "cron/portfolio"


async def sync_portfolio(*, portfolio: PortfolioSync,
                         logger: LeveledLogger) -> None:
    """Reconcile holdings against the venues.

    A discrepancy is logged at error level even though the sync succeeded: it
    means our record disagreed with the exchange, which is the loudest thing
    this system can discover short of a failed order.
    """
    result = await portfolio.sync(SyncRequest())
    if result.discrepancies:
        await logger.error(TAG, "portfolio disagrees with the venues", {
            "count": len(result.discrepancies),
            "symbols": [f"{d.symbol.base}/{d.symbol.quote}"
                        for d in result.discrepancies]})
    if result.unreachable:
        await logger.warn(TAG, "venues unreachable during sync",
                          {"venues": [str(v) for v in result.unreachable]})
    await logger.info(TAG, "portfolio synced", {"equity": str(result.portfolio.equity)})
