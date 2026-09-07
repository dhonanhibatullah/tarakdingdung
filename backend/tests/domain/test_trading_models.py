import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import (
    CyclePlan, OrderPlan, OrderType, PlannedOrder, Side, TargetWeights, TimeInForce,
)
from tarakdingdung.domain.models.backtest import TimeRange
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    CollectionFailure, Discrepancy, ExecutionResult, OrderAck, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
TS = 1_757_000_000_000
NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)


def order() -> PlannedOrder:
    return PlannedOrder(symbol=BTC, side=Side.BUY, type=OrderType.MARKET,
                        quantity=Decimal("1"), price=None,
                        time_in_force=TimeInForce.IOC, client_order_id="tdd0123456789abcd")


# --- TimeRange --------------------------------------------------------------

def test_time_range_accepts_an_advancing_window():
    assert TimeRange(start=TS, end=TS + 1000).duration == 1000


@pytest.mark.parametrize("start,end", [(TS, TS), (TS + 1, TS)])
def test_time_range_rejects_a_non_advancing_window(start, end):
    # A reversed window selects nothing rather than failing, which would report
    # a backtest over no data as an empty success.
    with pytest.raises(DomainError) as e:
        TimeRange(start=start, end=end)
    assert e.value.type is ErrorType.VALIDATION


# --- CyclePlan --------------------------------------------------------------

def test_cycle_plan_reports_whether_it_halted():
    empty = OrderPlan(orders=(), rejected=())
    weights = TargetWeights(timestamp=TS, weights={})
    assert CyclePlan(timestamp=TS, weights=weights, orders=empty).is_halted is False
    assert CyclePlan(timestamp=TS, weights=weights, orders=empty,
                     halted_by="HaltFlagRiskRule").is_halted is True


# --- ExecutionResult --------------------------------------------------------

def test_execution_result_is_complete_without_unconfirmed_orders():
    result = ExecutionResult(
        accepted=(OrderAck(order=order(), client_order_id="a", venue_order_id="v"),),
        rejected=(), unconfirmed=(), fills=())
    assert result.is_complete is True


def test_execution_result_is_incomplete_with_an_unconfirmed_order():
    # An unconfirmed order may or may not exist at the venue; the cycle must
    # know it has to reconcile rather than assume success.
    result = ExecutionResult(
        accepted=(), rejected=(),
        unconfirmed=(UnconfirmedOrder(order=order(), client_order_id="a",
                                      reason="timeout"),),
        fills=())
    assert result.is_complete is False


# --- Discrepancy ------------------------------------------------------------

@pytest.mark.parametrize("expected,actual,difference", [
    ("1", "1.5", "0.5"),
    ("2", "1", "-1"),
    ("1", "1", "0"),
])
def test_discrepancy_difference_is_signed(expected, actual, difference):
    gap = Discrepancy(symbol=BTC, expected=Decimal(expected), actual=Decimal(actual))
    assert gap.difference == Decimal(difference)


def test_collection_failure_can_be_venue_wide():
    # A whole venue being unreachable has no single symbol to blame.
    failure = CollectionFailure(venue=Venue.INDODAX, symbol=None, reason="timeout")
    assert failure.symbol is None


# --- StrategyConfig ---------------------------------------------------------

def test_strategy_config_carries_its_mode():
    config = StrategyConfig(
        id=uuid.uuid4(), name="momentum", description="", kind="pipeline",
        mode=TradingMode.PAPER, universe=(BTC,), parameters={}, is_enabled=True,
        preferences={}, created_at=NOW)
    assert config.mode is TradingMode.PAPER
    with pytest.raises(Exception):
        config.mode = TradingMode.LIVE
