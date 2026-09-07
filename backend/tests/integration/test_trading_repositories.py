"""Exercises the SQL the trading repositories actually emit.

The interesting parts here cannot be covered by fakes: ON CONFLICT upserts,
DISTINCT ON for latest-per-symbol, the freshness bound applied in SQL, and
NUMERIC round-tripping without a float in the middle.
"""

from decimal import Decimal

import pytest
import sqlalchemy as sa

from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.execution import ExecutionResult, OrderState
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, TimeRange, Venue,
)
from tarakdingdung.domain.models.performance import (
    EquityPoint, Fill, OverfittingReport, PerformanceReport, TrialResult,
)
from tarakdingdung.domain.models.portfolio import Portfolio, Position
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.infrastructure.repository.backtest.repository import (
    SqlAlchemyBacktestRepository,
)
from tarakdingdung.infrastructure.repository.market_data.repository import (
    SqlAlchemyMarketDataRepository,
)
from tarakdingdung.infrastructure.repository.order_journal.repository import (
    SqlAlchemyOrderJournalRepository,
)
from tarakdingdung.infrastructure.repository.portfolio.repository import (
    SqlAlchemyPortfolioRepository,
)
from tarakdingdung.infrastructure.repository.strategy.repository import (
    SqlAlchemyStrategyRepository,
)

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
ETH = Symbol(venue=Venue.TOKOCRYPTO, base="ETH", quote="USDT")
TS = 1_757_000_000_000
HOUR = 3_600_000


def candle(open_time: int, close: str = "100") -> Candle:
    return Candle(open_time=open_time, open=Decimal("1"), high=Decimal("2"),
                  low=Decimal("0.5"), close=Decimal(close), volume=Decimal("10"))


@pytest.fixture
def market(db):
    return SqlAlchemyMarketDataRepository(db)


@pytest.fixture
def strategies(db):
    return SqlAlchemyStrategyRepository(db)


@pytest.fixture
def portfolios(db):
    return SqlAlchemyPortfolioRepository(db)


@pytest.fixture
def journal(db):
    return SqlAlchemyOrderJournalRepository(db)


@pytest.fixture
def backtests(db):
    return SqlAlchemyBacktestRepository(db)


# --- market data ------------------------------------------------------------

@pytest.mark.asyncio
async def test_candles_round_trip_without_losing_precision(market):
    exact = Decimal("0.000000000000000001")
    await market.write_candles(symbol=BTC, interval="1h", candles=(
        Candle(open_time=TS, open=exact, high=exact, low=exact, close=exact,
               volume=exact),))
    found = await market.read_candles(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + 1))
    assert found[0].close == exact


@pytest.mark.asyncio
async def test_rewriting_a_candle_updates_rather_than_duplicating(market):
    # Collection re-fetches overlapping windows every pass; a venue revising a
    # candle is a correction, not a conflict.
    await market.write_candles(symbol=BTC, interval="1h",
                               candles=(candle(TS, close="100"),))
    await market.write_candles(symbol=BTC, interval="1h",
                               candles=(candle(TS, close="123"),))
    found = await market.read_candles(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + 1))
    assert len(found) == 1
    assert found[0].close == Decimal("123")


@pytest.mark.asyncio
async def test_candles_are_scoped_by_symbol_and_interval(market):
    await market.write_candles(symbol=BTC, interval="1h", candles=(candle(TS),))
    await market.write_candles(symbol=BTC, interval="1d", candles=(candle(TS),))
    await market.write_candles(symbol=ETH, interval="1h", candles=(candle(TS),))
    window = TimeRange(start=TS, end=TS + 1)
    assert len(await market.read_candles(symbol=BTC, interval="1h", window=window)) == 1


@pytest.mark.asyncio
async def test_prices_return_only_the_latest_within_the_freshness_bound(market):
    await market.write_price(symbol=BTC, timestamp=TS - 100, price=Decimal("90"))
    await market.write_price(symbol=BTC, timestamp=TS, price=Decimal("100"))
    fresh = await market.read_prices(symbols=(BTC,), as_of=TS, max_age=1000)
    assert fresh == {BTC: Decimal("100")}


@pytest.mark.asyncio
async def test_a_stale_price_is_omitted_by_the_query_not_by_python(market):
    await market.write_price(symbol=BTC, timestamp=TS - 10_000, price=Decimal("90"))
    assert await market.read_prices(symbols=(BTC,), as_of=TS, max_age=1_000) == {}


@pytest.mark.asyncio
async def test_a_future_price_is_never_returned(market):
    await market.write_price(symbol=BTC, timestamp=TS + 10_000, price=Decimal("90"))
    assert await market.read_prices(symbols=(BTC,), as_of=TS, max_age=100_000) == {}


@pytest.mark.asyncio
async def test_prices_are_per_symbol(market):
    await market.write_price(symbol=BTC, timestamp=TS, price=Decimal("100"))
    await market.write_price(symbol=ETH, timestamp=TS, price=Decimal("50"))
    found = await market.read_prices(symbols=(BTC, ETH), as_of=TS, max_age=1000)
    assert found == {BTC: Decimal("100"), ETH: Decimal("50")}


@pytest.mark.asyncio
async def test_books_round_trip_and_return_the_latest_before_the_instant(market):
    old = OrderBook(symbol=BTC, timestamp=TS - 10, bids=(), asks=())
    new = OrderBook(symbol=BTC, timestamp=TS,
                    bids=(BookLevel(price=Decimal("99.5"), quantity=Decimal("1.25")),),
                    asks=(BookLevel(price=Decimal("100.5"), quantity=Decimal("2")),))
    await market.write_book(old)
    await market.write_book(new)
    found = await market.read_book(symbol=BTC, as_of=TS)
    assert found.timestamp == TS
    assert found.bids[0].price == Decimal("99.5")
    assert found.asks[0].quantity == Decimal("2")


@pytest.mark.asyncio
async def test_rules_upsert_in_place(market):
    def rules(tick: str) -> SymbolRules:
        return SymbolRules(symbol=BTC, tick_size=Decimal(tick),
                           step_size=Decimal("0.001"), min_notional=Decimal("10"),
                           maker_fee=Decimal("0.001"), taker_fee=Decimal("0.002"))

    await market.write_rules({BTC: rules("0.01")})
    await market.write_rules({BTC: rules("0.05")})
    found = await market.read_rules(symbols=(BTC,))
    assert found[BTC].tick_size == Decimal("0.05")


@pytest.mark.asyncio
async def test_snapshot_includes_only_symbols_with_a_fresh_price(market):
    # A candle history with no current price cannot be sized against, so a
    # strategy must not be able to rank it.
    await market.write_candles(symbol=BTC, interval="1h", candles=(candle(TS),))
    await market.write_candles(symbol=ETH, interval="1h", candles=(candle(TS),))
    await market.write_price(symbol=BTC, timestamp=TS, price=Decimal("100"))
    snapshot = await market.read_snapshot(symbols=(BTC, ETH), as_of=TS,
                                          interval="1h", lookback=10, max_age=1000)
    assert set(snapshot.last_prices) == {BTC}
    assert set(snapshot.candles) == {BTC}


@pytest.mark.asyncio
async def test_snapshot_never_carries_a_candle_from_the_future(market):
    await market.write_candles(symbol=BTC, interval="1h", candles=(
        candle(TS - HOUR), candle(TS), candle(TS + HOUR)))
    await market.write_price(symbol=BTC, timestamp=TS, price=Decimal("100"))
    snapshot = await market.read_snapshot(symbols=(BTC,), as_of=TS, interval="1h",
                                          lookback=10, max_age=1000)
    assert [c.open_time for c in snapshot.candles[BTC]] == [TS - HOUR, TS]


@pytest.mark.asyncio
async def test_coverage_finds_the_hole(market):
    # One candle missing in the middle of an otherwise hourly series.
    await market.write_candles(symbol=BTC, interval="1h", candles=(
        candle(TS), candle(TS + HOUR), candle(TS + HOUR * 3)))
    coverage = await market.read_coverage(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + HOUR * 4))
    assert coverage.present == 3
    assert coverage.expected == 4
    assert len(coverage.gaps) == 1
    assert coverage.gaps[0] == TimeRange(start=TS + HOUR * 2, end=TS + HOUR * 3)
    assert coverage.completeness == 0.75


@pytest.mark.asyncio
async def test_complete_coverage_reports_no_gaps(market):
    await market.write_candles(symbol=BTC, interval="1h", candles=tuple(
        candle(TS + HOUR * i) for i in range(4)))
    coverage = await market.read_coverage(
        symbol=BTC, interval="1h", window=TimeRange(start=TS, end=TS + HOUR * 4))
    assert coverage.gaps == ()
    assert coverage.completeness == 1.0


# --- strategy ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_strategy_round_trips_its_universe(strategies):
    new_id = await strategies.create(
        name="momentum", description="cross-sectional", kind="pipeline",
        mode=TradingMode.PAPER, universe=(BTC, ETH), parameters={"window": 30},
        is_enabled=True, created_by=None)
    found = await strategies.read_by_id(new_id)
    assert found.universe == (BTC, ETH)
    assert found.parameters == {"window": 30}
    assert found.mode is TradingMode.PAPER


@pytest.mark.asyncio
async def test_only_enabled_strategies_are_returned(strategies):
    await strategies.create(name="on", description=None, kind="pipeline",
                            mode=TradingMode.PAPER, universe=(BTC,),
                            parameters=None, is_enabled=True, created_by=None)
    await strategies.create(name="off", description=None, kind="pipeline",
                            mode=TradingMode.PAPER, universe=(BTC,),
                            parameters=None, is_enabled=False, created_by=None)
    assert [s.name for s in await strategies.read_enabled()] == ["on"]


@pytest.mark.asyncio
async def test_a_soft_deleted_strategy_frees_its_name(strategies):
    first = await strategies.create(name="reused", description=None, kind="pipeline",
                                    mode=TradingMode.PAPER, universe=(BTC,),
                                    parameters=None, is_enabled=None, created_by=None)
    await strategies.delete_by_id(first)
    again = await strategies.create(name="reused", description=None, kind="pipeline",
                                    mode=TradingMode.LIVE, universe=(BTC,),
                                    parameters=None, is_enabled=None, created_by=None)
    assert again != first


# --- portfolio --------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_snapshot_round_trips(portfolios):
    portfolio = Portfolio(
        timestamp=TS, cash={Venue.INDODAX: Decimal("1234.56")},
        positions={BTC: Position(symbol=BTC, quantity=Decimal("0.5"),
                                 average_price=Decimal("100000"))},
        equity=Decimal("51234.56"))
    await portfolios.write_snapshot(portfolio)
    found = await portfolios.read_latest(as_of=TS)
    assert found.cash[Venue.INDODAX] == Decimal("1234.56")
    assert found.positions[BTC].quantity == Decimal("0.5")
    assert found.equity == Decimal("51234.56")


@pytest.mark.asyncio
async def test_risk_state_is_derived_from_the_equity_curve(portfolios):
    for offset, equity in ((0, "1000"), (1000, "1500"), (2000, "1200")):
        await portfolios.write_equity_point(
            EquityPoint(timestamp=TS + offset, equity=Decimal(equity)))
    state = await portfolios.read_risk_state(as_of=TS + 2000)
    assert state.equity_peak == Decimal("1500")
    assert state.daily_pnl == Decimal("200")


@pytest.mark.asyncio
async def test_fills_round_trip_within_a_window(portfolios):
    await portfolios.append_fills((
        Fill(symbol=BTC, side=Side.BUY, quantity=Decimal("1"), price=Decimal("100"),
             fee=Decimal("0.2"), timestamp=TS),
        Fill(symbol=ETH, side=Side.SELL, quantity=Decimal("2"), price=Decimal("50"),
             fee=Decimal("0.1"), timestamp=TS + 5000),))
    found = await portfolios.read_fills(window=TimeRange(start=TS, end=TS + 1000))
    assert len(found) == 1
    assert found[0].side is Side.BUY


@pytest.mark.asyncio
async def test_halt_upserts_and_defaults_to_clear(portfolios, strategies):
    sid = await strategies.create(name="halted", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    assert await portfolios.read_halt(strategy_id=sid) == (False, None)
    await portfolios.set_halt(strategy_id=sid, halted=True, reason="cancel failed")
    await portfolios.set_halt(strategy_id=sid, halted=True, reason="still failing")
    assert await portfolios.read_halt(strategy_id=sid) == (True, "still failing")


# --- order journal ----------------------------------------------------------

def planned(client_order_id: str = "tdd0000000000001") -> PlannedOrder:
    return PlannedOrder(symbol=BTC, side=Side.BUY, type=OrderType.LIMIT,
                        quantity=Decimal("1.5"), price=Decimal("100.25"),
                        time_in_force=TimeInForce.GTC,
                        client_order_id=client_order_id)


@pytest.mark.asyncio
async def test_planned_orders_start_unreconciled(journal, strategies):
    sid = await strategies.create(name="j1", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    await journal.write_planned(strategy_id=sid, timestamp=TS, orders=(planned(),))
    pending = await journal.read_unreconciled(strategy_id=sid)
    assert [o.client_order_id for o in pending] == ["tdd0000000000001"]
    assert pending[0].quantity == Decimal("1.5")


@pytest.mark.asyncio
async def test_a_settled_order_leaves_the_reconciliation_queue(journal, strategies):
    sid = await strategies.create(name="j2", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    await journal.write_planned(strategy_id=sid, timestamp=TS, orders=(planned(),))
    await journal.set_state(client_order_id="tdd0000000000001",
                            state=OrderState.ACCEPTED, venue_order_id="v1", reason=None)
    assert await journal.read_unreconciled(strategy_id=sid) == ()


@pytest.mark.asyncio
async def test_an_unconfirmed_order_stays_in_the_queue(journal, strategies):
    sid = await strategies.create(name="j3", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    await journal.write_planned(strategy_id=sid, timestamp=TS, orders=(planned(),))
    await journal.set_state(client_order_id="tdd0000000000001",
                            state=OrderState.UNCONFIRMED, venue_order_id=None,
                            reason="timeout")
    assert len(await journal.read_unreconciled(strategy_id=sid)) == 1


@pytest.mark.asyncio
async def test_replaying_a_cycle_does_not_reset_a_settled_order(journal, strategies, db):
    # A replayed cycle journals the same client order id; doing nothing on
    # conflict preserves the verdict the first attempt reached.
    sid = await strategies.create(name="j4", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    await journal.write_planned(strategy_id=sid, timestamp=TS, orders=(planned(),))
    await journal.set_state(client_order_id="tdd0000000000001",
                            state=OrderState.ACCEPTED, venue_order_id="v1", reason=None)
    await journal.write_planned(strategy_id=sid, timestamp=TS, orders=(planned(),))

    async with db.session() as s:
        count = await s.scalar(sa.text(
            "SELECT count(*) FROM planned_orders WHERE client_order_id = :c"),
            {"c": "tdd0000000000001"})
    assert count == 1
    assert await journal.read_unreconciled(strategy_id=sid) == ()


# --- backtest ---------------------------------------------------------------

def report() -> PerformanceReport:
    return PerformanceReport(total_return=0.1, sharpe=1.2, sortino=1.5,
                             max_drawdown=0.2, turnover=3.0, gross_return=0.15,
                             net_return=0.1, cost_drag=0.05, trade_count=42)


@pytest.mark.asyncio
async def test_backtest_run_round_trips(backtests, strategies):
    sid = await strategies.create(name="bt", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    window = TimeRange(start=TS, end=TS + HOUR * 10)
    run_id = await backtests.create_run(strategy_id=sid, window=window,
                                        initial_equity=Decimal("10000"),
                                        report=report(), created_by=None)
    found = await backtests.read_run_by_id(run_id)
    assert found.window == window
    assert found.report.sharpe == 1.2
    assert found.report.trade_count == 42


@pytest.mark.asyncio
async def test_validation_run_keeps_every_trial(backtests, strategies):
    # The overfitting probability is only interpretable alongside the trials
    # that produced it, so all of them are stored.
    sid = await strategies.create(name="val", description=None, kind="pipeline",
                                  mode=TradingMode.PAPER, universe=(BTC,),
                                  parameters=None, is_enabled=None, created_by=None)
    trials = tuple(TrialResult(label=f"trial-{i}", parameters={"n": str(i)},
                               returns=(0.01, 0.02)) for i in range(5))
    validation_id = await backtests.create_validation(
        strategy_id=sid, window=TimeRange(start=TS, end=TS + HOUR),
        trials=trials,
        overfitting=OverfittingReport(probability=0.05, threshold=0.1, passed=True),
        created_by=None)
    found = await backtests.read_validation_by_id(validation_id)
    assert len(found.trials) == 5
    assert found.trials[0].returns == (0.01, 0.02)
    assert found.overfitting.passed is True
