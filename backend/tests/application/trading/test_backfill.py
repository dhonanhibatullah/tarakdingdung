from decimal import Decimal

from tarakdingdung.application.trading.backtest.backfill import backfill
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.symbol import Symbol
from tests.fakes.trading import InMemoryMarketDataRepository


class FakeMarketSource:
    def __init__(self) -> None:
        self.calls = []

    async def fetch_candles(self, symbol, interval, from_ms, to_ms):
        self.calls.append((symbol.external, from_ms, to_ms))
        n = (to_ms - from_ms) // 1000
        return [
            Candle(
                symbol_id=symbol.id,
                open_time_ms=from_ms + i * 1000,
                open=Decimal("1"),
                high=Decimal("1"),
                low=Decimal("1"),
                close=Decimal("1"),
                volume=Decimal("1"),
            )
            for i in range(n)
        ]

    async def fetch_ticker(self, symbol):
        raise NotImplementedError


async def test_backfill_paginates_and_appends():
    symbols = [Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]
    source = FakeMarketSource()
    market_data = InMemoryMarketDataRepository()

    total = await backfill(source, market_data, symbols, "1D", 0, 3000, step_ms=1000)

    assert total == 3
    assert len(source.calls) == 3
    assert len(market_data.candles) == 3
