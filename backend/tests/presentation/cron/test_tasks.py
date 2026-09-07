import uuid
from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import OrderPlan, TargetWeights
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import CollectionFailure, Discrepancy
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.usecases.trading.collection import CollectResult
from tarakdingdung.domain.usecases.trading.engine import CycleDecision, RunCycleResult
from tarakdingdung.domain.usecases.trading.portfolio import SyncResult
from tarakdingdung.presentation.cron.tasks.collect import collect_market_data
from tarakdingdung.presentation.cron.tasks.engine import run_cycles
from tarakdingdung.presentation.cron.tasks.portfolio import sync_portfolio
from tests.fakes.trading import (
    TS, FakeStrategyRepository, make_portfolio, make_strategy,
)
from tests.fakes.utilities import NullLogger

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")


class SpyLogger(NullLogger):
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    async def error(self, tag, message, meta) -> None:
        self.records.append(("error", message))

    async def warn(self, tag, message, meta) -> None:
        self.records.append(("warn", message))

    async def info(self, tag, message, meta) -> None:
        self.records.append(("info", message))

    def levels(self) -> set[str]:
        return {level for level, _ in self.records}


class StubCollection:
    def __init__(self, result) -> None:
        self.result = result

    async def collect(self, request):
        return self.result


class StubPortfolio:
    def __init__(self, result) -> None:
        self.result = result

    async def sync(self, request):
        return self.result

    async def read_current(self, venue=None): ...
    async def read_equity_curve(self, request): ...


class StubEngine:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls = []

    async def run_cycle(self, request):
        self.calls.append(request.strategy_id)
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def cycle(decision, **kw) -> RunCycleResult:
    base = dict(timestamp=TS, strategy_id=uuid.uuid4(), decision=decision)
    return RunCycleResult(**{**base, **kw})


# --- collect ----------------------------------------------------------------

async def test_a_clean_collection_logs_at_info():
    logger = SpyLogger()
    await collect_market_data(
        collection=StubCollection(CollectResult(
            timestamp=TS, collected=(BTC,), candles_written=10, failed=())),
        logger=logger, interval="1h")
    assert logger.levels() == {"info"}


async def test_a_partial_collection_warns_without_raising():
    # One venue down must not stop the scheduler.
    logger = SpyLogger()
    await collect_market_data(
        collection=StubCollection(CollectResult(
            timestamp=TS, collected=(), candles_written=0,
            failed=(CollectionFailure(venue=Venue.INDODAX, symbol=BTC,
                                      reason="venue down"),))),
        logger=logger, interval="1h")
    assert logger.levels() == {"warn"}


# --- portfolio --------------------------------------------------------------

async def test_a_discrepancy_is_logged_at_error_even_though_sync_succeeded():
    # Our record disagreeing with the exchange is the loudest thing this
    # system can find short of a failed order.
    logger = SpyLogger()
    await sync_portfolio(
        portfolio=StubPortfolio(SyncResult(
            portfolio=make_portfolio(),
            discrepancies=(Discrepancy(symbol=BTC, expected=Decimal("5"),
                                       actual=Decimal("2")),),
            unreachable=())),
        logger=logger)
    assert "error" in logger.levels()


async def test_an_unreachable_venue_warns():
    logger = SpyLogger()
    await sync_portfolio(
        portfolio=StubPortfolio(SyncResult(
            portfolio=make_portfolio(), discrepancies=(),
            unreachable=(Venue.TOKOCRYPTO,))),
        logger=logger)
    assert "warn" in logger.levels()


async def test_a_clean_sync_only_logs_info():
    logger = SpyLogger()
    await sync_portfolio(
        portfolio=StubPortfolio(SyncResult(
            portfolio=make_portfolio(), discrepancies=(), unreachable=())),
        logger=logger)
    assert logger.levels() == {"info"}


# --- engine -----------------------------------------------------------------

async def test_every_enabled_strategy_is_stepped():
    strategies = FakeStrategyRepository((make_strategy(name="a"), make_strategy(name="b")))
    engine = StubEngine([cycle(CycleDecision.TRADED), cycle(CycleDecision.NO_DRIFT)])
    await run_cycles(engine=engine, strategies=strategies, logger=SpyLogger())
    assert len(engine.calls) == 2


async def test_a_disabled_strategy_is_not_stepped():
    strategies = FakeStrategyRepository((make_strategy(is_enabled=False),))
    engine = StubEngine([])
    await run_cycles(engine=engine, strategies=strategies, logger=SpyLogger())
    assert engine.calls == []


async def test_one_failing_strategy_does_not_stop_the_others():
    # A single misconfigured strategy would otherwise silently halt trading
    # for every other one.
    strategies = FakeStrategyRepository((make_strategy(name="a"), make_strategy(name="b")))
    engine = StubEngine([DomainError("bad config", ErrorType.BAD_ARGS),
                         cycle(CycleDecision.TRADED)])
    logger = SpyLogger()
    await run_cycles(engine=engine, strategies=strategies, logger=logger)
    assert len(engine.calls) == 2
    assert "error" in logger.levels()


async def test_a_halt_is_logged_louder_than_a_trade():
    strategies = FakeStrategyRepository((make_strategy(),))
    engine = StubEngine([cycle(CycleDecision.HALTED, halted_by="HaltFlagRiskRule",
                               weights=TargetWeights(timestamp=TS, weights={}),
                               plan=OrderPlan(orders=(), rejected=()))])
    logger = SpyLogger()
    await run_cycles(engine=engine, strategies=strategies, logger=logger)
    assert "warn" in logger.levels()


async def test_a_routine_cycle_logs_at_info():
    strategies = FakeStrategyRepository((make_strategy(),))
    engine = StubEngine([cycle(CycleDecision.NO_DRIFT)])
    logger = SpyLogger()
    await run_cycles(engine=engine, strategies=strategies, logger=logger)
    assert logger.levels() == {"info"}
