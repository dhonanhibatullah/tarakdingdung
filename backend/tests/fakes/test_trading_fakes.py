"""The fakes are test infrastructure, so they get their own coverage: a fake
that quietly diverges from its contract makes every test using it a lie."""

import uuid
from decimal import Decimal

import pytest

from tarakdingdung.domain.models.execution import OrderState
from tarakdingdung.domain.models.market import Symbol, TimeRange, Venue
from tarakdingdung.domain.models.performance import EquityPoint
from tarakdingdung.domain.models.strategy import TradingMode
from tests.fakes.trading import (
    TS, FakeExecutor, FakeMarketDataRepository, FakeOrderJournalRepository,
    FakePortfolioRepository, FakeSingleFlight, FakeStrategyRepository, make_strategy,
)

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")


@pytest.mark.asyncio
async def test_single_flight_admits_one_holder():
    lock = FakeSingleFlight()
    assert await lock.acquire("s") is True
    assert await lock.acquire("s") is False
    await lock.release("s")
    assert await lock.acquire("s") is True


@pytest.mark.asyncio
async def test_strategy_repository_reads_only_enabled():
    repo = FakeStrategyRepository((make_strategy(is_enabled=True),
                                   make_strategy(is_enabled=False)))
    assert len(await repo.read_enabled()) == 1


@pytest.mark.asyncio
async def test_strategy_repository_filters_by_mode():
    repo = FakeStrategyRepository((make_strategy(mode=TradingMode.LIVE),
                                   make_strategy(mode=TradingMode.PAPER)))
    found, total = await repo.read_by_pagination(page=1, limit=10, search=None,
                                                 mode=TradingMode.LIVE)
    assert total == 1 and found[0].mode is TradingMode.LIVE


@pytest.mark.asyncio
async def test_market_data_omits_stale_prices():
    repo = FakeMarketDataRepository()
    await repo.write_price(symbol=BTC, timestamp=TS - 10_000, price=Decimal("100"))
    fresh = await repo.read_prices(symbols=(BTC,), as_of=TS, max_age=60_000)
    stale = await repo.read_prices(symbols=(BTC,), as_of=TS, max_age=1_000)
    assert fresh == {BTC: Decimal("100")}
    assert stale == {}


@pytest.mark.asyncio
async def test_market_data_never_returns_the_future():
    repo = FakeMarketDataRepository()
    await repo.write_price(symbol=BTC, timestamp=TS + 10_000, price=Decimal("100"))
    assert await repo.read_prices(symbols=(BTC,), as_of=TS, max_age=60_000) == {}


@pytest.mark.asyncio
async def test_portfolio_repository_windows_the_equity_curve():
    repo = FakePortfolioRepository()
    for offset in (0, 1000, 5000):
        await repo.write_equity_point(
            EquityPoint(timestamp=TS + offset, equity=Decimal("100")))
    found = await repo.read_equity_curve(window=TimeRange(start=TS, end=TS + 2000))
    assert len(found) == 2


@pytest.mark.asyncio
async def test_halt_defaults_to_clear_and_persists_once_set():
    repo = FakePortfolioRepository()
    strategy_id = uuid.uuid4()
    assert await repo.read_halt(strategy_id=strategy_id) == (False, None)
    await repo.set_halt(strategy_id=strategy_id, halted=True, reason="cancel failed")
    assert await repo.read_halt(strategy_id=strategy_id) == (True, "cancel failed")


@pytest.mark.asyncio
async def test_executor_reports_transport_failure_as_unconfirmed():
    # Not rejected: the order may exist at the venue, and the difference is
    # the whole reason reconciliation exists.
    from tests.infrastructure.algorithm.conformance import BTC_IDX
    from tarakdingdung.domain.models.algorithm import (
        OrderType, PlannedOrder, Side, TimeInForce,
    )
    order = PlannedOrder(symbol=BTC_IDX, side=Side.BUY, type=OrderType.MARKET,
                         quantity=Decimal("1"), price=None,
                         time_in_force=TimeInForce.IOC, client_order_id="tdd1")
    result = await FakeExecutor(fail_submit=True).submit((order,))
    assert result.is_complete is False
    assert result.unconfirmed[0].client_order_id == "tdd1"
    assert result.rejected == ()


@pytest.mark.asyncio
async def test_journal_records_the_order_of_events():
    # The ordering assertion the engine's write-ahead test depends on.
    journal = FakeOrderJournalRepository()
    executor = FakeExecutor(journal=journal)
    await journal.write_planned(strategy_id=uuid.uuid4(), timestamp=TS, orders=())
    await executor.submit(())
    assert journal.events == ["write_planned", "submit"]


@pytest.mark.asyncio
async def test_journal_tracks_order_state():
    journal = FakeOrderJournalRepository()
    await journal.set_state(client_order_id="tdd1", state=OrderState.ACCEPTED,
                            venue_order_id="v1", reason=None)
    assert journal.states["tdd1"] is OrderState.ACCEPTED
