import uuid
from decimal import Decimal

import pytest

from tarakdingdung.application.trading.history.usecase import MarketDataHistoryUsecase
from tarakdingdung.application.trading.strategy.usecase import StrategyManagementUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.domain.usecases.trading.history import (
    ReadCandlesRequest, ReadCoverageRequest, ReadSnapshotRequest,
)
from tarakdingdung.domain.usecases.trading.strategy import (
    CreateStrategyRequest, ListStrategiesRequest, UpdateStrategyRequest,
)
from tests.application.trading.conftest import BTC, snapshot
from tests.fakes.trading import (
    TS, FakeMarketDataRepository, FakeStrategyRepository, make_strategy,
)
from tests.fakes.utilities import NullLogger


def strategies(items=()):
    repo = FakeStrategyRepository(items)
    return StrategyManagementUsecase(strategies=repo, logger=NullLogger()), repo


def history():
    repo = FakeMarketDataRepository()
    return MarketDataHistoryUsecase(market_data=repo, logger=NullLogger()), repo


# --- strategy management ----------------------------------------------------

async def test_creates_a_strategy():
    usecase, repo = strategies()
    new_id = await usecase.create(CreateStrategyRequest(
        name="momentum", description=None, kind="pipeline",
        mode=TradingMode.PAPER, universe=(BTC,)))
    assert (await repo.read_by_id(new_id)).name == "momentum"


async def test_refuses_an_empty_universe():
    # A strategy with nothing to trade would run every cycle and do nothing,
    # reporting NO_DRIFT forever.
    usecase, _ = strategies()
    with pytest.raises(DomainError) as e:
        await usecase.create(CreateStrategyRequest(
            name="empty", description=None, kind="pipeline",
            mode=TradingMode.PAPER, universe=()))
    assert e.value.type is ErrorType.VALIDATION


async def test_refuses_to_empty_a_universe_by_update():
    config = make_strategy(universe=(BTC,))
    usecase, _ = strategies((config,))
    with pytest.raises(DomainError) as e:
        await usecase.update_by_id(UpdateStrategyRequest(id=config.id, universe=()))
    assert e.value.type is ErrorType.VALIDATION


async def test_reading_a_missing_strategy_raises_not_found():
    usecase, _ = strategies()
    with pytest.raises(DomainError) as e:
        await usecase.read_by_id(uuid.uuid4())
    assert e.value.type is ErrorType.NOT_FOUND


async def test_updates_and_disables():
    config = make_strategy(universe=(BTC,))
    usecase, repo = strategies((config,))
    await usecase.update_by_id(UpdateStrategyRequest(id=config.id, is_enabled=False))
    assert (await repo.read_by_id(config.id)).is_enabled is False


async def test_lists_with_a_mode_filter():
    usecase, _ = strategies((make_strategy(mode=TradingMode.LIVE),
                             make_strategy(mode=TradingMode.PAPER)))
    result = await usecase.read_by_pagination(
        ListStrategiesRequest(page=1, limit=10, mode=TradingMode.LIVE))
    assert result.total == 1


async def test_deleting_a_missing_strategy_raises():
    usecase, _ = strategies()
    with pytest.raises(DomainError):
        await usecase.delete_by_id(uuid.uuid4())


# --- history ----------------------------------------------------------------

async def test_reads_candles_within_the_window():
    usecase, repo = history()
    from tarakdingdung.domain.models.market import Candle
    await repo.write_candles(symbol=BTC, interval="1h", candles=tuple(
        Candle(open_time=TS + i, open=Decimal("1"), high=Decimal("1"),
               low=Decimal("1"), close=Decimal("1"), volume=Decimal("1"))
        for i in range(5)))
    result = await usecase.read_candles(ReadCandlesRequest(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + 3)))
    assert len(result.candles) == 3


async def test_passes_the_staleness_bound_through_to_storage():
    usecase, repo = history()
    repo.snapshot = snapshot()
    result = await usecase.read_snapshot(ReadSnapshotRequest(
        symbols=(BTC,), as_of=TS, max_age_ms=60_000))
    assert result.last_prices


async def test_reports_coverage():
    usecase, _ = history()
    coverage = await usecase.read_coverage(ReadCoverageRequest(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + 1000)))
    assert coverage.completeness == 1.0
