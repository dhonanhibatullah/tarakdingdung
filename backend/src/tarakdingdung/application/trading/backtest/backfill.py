from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.scrapper.market_source import MarketSource
from tarakdingdung.domain.models.symbol import Symbol


async def backfill(
    market_source: MarketSource,
    market_data: MarketDataRepository,
    symbols: list[Symbol],
    interval: str,
    from_ms: int,
    to_ms: int,
    step_ms: int,
) -> int:
    total = 0
    for symbol in symbols:
        cursor = from_ms
        while cursor < to_ms:
            end = min(cursor + step_ms, to_ms)
            candles = await market_source.fetch_candles(symbol, interval, cursor, end)
            await market_data.append_candles(candles)
            total += len(candles)
            cursor = end
    return total
