from decimal import Decimal
from uuid import uuid4

import pytest

from tarakdingdung.domain.models.algorithm import Side
from tarakdingdung.infrastructure.algorithm.allocation.equal_weight import EqualWeightAllocator
from tarakdingdung.infrastructure.algorithm.cycle.identifiers import client_order_id
from tarakdingdung.infrastructure.algorithm.cycle.standard import StandardCyclePlanner
from tarakdingdung.infrastructure.algorithm.feature.rolling_window import (
    RollingWindowFeatureExtractor,
)
from tarakdingdung.infrastructure.algorithm.order.venue_rule import VenueRuleOrderPlanner
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tarakdingdung.infrastructure.algorithm.risk.halt_flag import HaltFlagRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import (
    VolatilityKillSwitchRiskRule,
)
from tarakdingdung.infrastructure.algorithm.signal.cross_sectional_momentum import (
    CrossSectionalMomentumSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.strategy.pipeline import PipelineStrategy
from tarakdingdung.infrastructure.algorithm.universe.static import StaticUniverseSelector
from tests.infrastructure.algorithm import conformance
from tests.infrastructure.algorithm.conformance import (
    BTC_IDX, ETH_IDX, TS, portfolio, position, risk_state, rules,
)
from tests.infrastructure.algorithm.fixtures import candles, snapshot

RISING = candles([100.0, 101.0, 102.0, 103.0, 120.0])
FALLING = candles([100.0, 99.0, 98.0, 97.0, 80.0])
SYMBOL_RULES = {BTC_IDX: rules(BTC_IDX), ETH_IDX: rules(ETH_IDX)}


def market() -> object:
    return snapshot(
        candle_map={BTC_IDX: RISING, ETH_IDX: FALLING},
        books={BTC_IDX: conformance.book(BTC_IDX), ETH_IDX: conformance.book(ETH_IDX)},
        prices={BTC_IDX: Decimal("100"), ETH_IDX: Decimal("100")})


def planner(*, risk_rules=()) -> StandardCyclePlanner:
    return StandardCyclePlanner(
        strategy=PipelineStrategy(
            universe=StaticUniverseSelector((BTC_IDX, ETH_IDX)),
            features=RollingWindowFeatureExtractor(momentum_window=3, fast_window=2,
                                                   slow_window=3, volatility_window=3),
            signals=CrossSectionalMomentumSignalGenerator(),
            allocator=EqualWeightAllocator()),
        risk_rules=risk_rules,
        rebalancer=NoTradeBandRebalancer(band=0.01),
        order_planner=VenueRuleOrderPlanner())


# --- conformance ------------------------------------------------------------

def test_conforms():
    conformance.assert_cycle_planner_conforms(planner(), market())


def test_halting_planner_conforms():
    conformance.assert_cycle_planner_halts(
        planner(risk_rules=(HaltFlagRiskRule(),)), market())


# --- behaviour --------------------------------------------------------------

def test_produces_orders_from_a_strategy_decision():
    plan = planner().plan(strategy_id=uuid4(), snapshot=market(),
                          portfolio=portfolio(equity="10000"),
                          state=risk_state(), rules=SYMBOL_RULES)
    assert plan.orders.orders
    assert plan.halted_by is None
    assert plan.weights.weights[BTC_IDX] > 0


def test_names_the_rule_that_halted():
    plan = planner(risk_rules=(
        PerPositionCapRiskRule(max_weight=0.5),
        VolatilityKillSwitchRiskRule(max_volatility=0.1),
    )).plan(strategy_id=uuid4(), snapshot=market(),
            portfolio=portfolio(equity="10000"),
            state=risk_state(volatility=0.9), rules=SYMBOL_RULES)
    assert plan.halted_by == "VolatilityKillSwitchRiskRule"


def test_attributes_the_halt_to_the_first_rule_that_flattened():
    plan = planner(risk_rules=(
        HaltFlagRiskRule(),
        VolatilityKillSwitchRiskRule(max_volatility=0.1),
    )).plan(strategy_id=uuid4(), snapshot=market(),
            portfolio=portfolio(equity="10000"),
            state=risk_state(volatility=0.9, halted=True), rules=SYMBOL_RULES)
    assert plan.halted_by == "HaltFlagRiskRule"


def test_a_halt_liquidates_rather_than_freezing():
    # Empty weights mean hold nothing, so what is held must be sold.
    plan = planner(risk_rules=(HaltFlagRiskRule(),)).plan(
        strategy_id=uuid4(), snapshot=market(),
        portfolio=portfolio(equity="10000", positions=[position(BTC_IDX, "50")]),
        state=risk_state(halted=True), rules=SYMBOL_RULES)
    assert plan.is_halted
    assert [o.side for o in plan.orders.orders] == [Side.SELL]


def test_caps_apply_without_halting():
    plan = planner(risk_rules=(PerPositionCapRiskRule(max_weight=0.1),)).plan(
        strategy_id=uuid4(), snapshot=market(),
        portfolio=portfolio(equity="10000"), state=risk_state(),
        rules=SYMBOL_RULES)
    assert plan.halted_by is None
    assert max(plan.weights.weights.values()) == pytest.approx(0.1)


def test_stamps_the_snapshot_timestamp():
    plan = planner().plan(strategy_id=uuid4(), snapshot=market(),
                          portfolio=portfolio(), state=risk_state(),
                          rules=SYMBOL_RULES)
    assert plan.timestamp == TS


def test_rejections_survive_into_the_plan():
    plan = planner().plan(
        strategy_id=uuid4(), snapshot=market(),
        portfolio=portfolio(equity="10000"), state=risk_state(),
        rules={BTC_IDX: rules(BTC_IDX, min_notional="100000000")})
    accounted = len(plan.orders.orders) + len(plan.orders.rejected)
    assert accounted > 0
    assert plan.orders.rejected


# --- client order ids -------------------------------------------------------

def test_client_order_id_is_deterministic():
    strategy_id = uuid4()
    args = dict(strategy_id=strategy_id, timestamp=TS, symbol=BTC_IDX, side=Side.BUY)
    assert client_order_id(**args) == client_order_id(**args)


def test_client_order_id_varies_with_every_component():
    base = dict(strategy_id=uuid4(), timestamp=TS, symbol=BTC_IDX, side=Side.BUY)
    variants = [
        {**base, "strategy_id": uuid4()},
        {**base, "timestamp": TS + 1},
        {**base, "symbol": ETH_IDX},
        {**base, "side": Side.SELL},
    ]
    ids = {client_order_id(**base)} | {client_order_id(**v) for v in variants}
    assert len(ids) == len(variants) + 1


def test_client_order_id_is_venue_safe():
    generated = client_order_id(strategy_id=uuid4(), timestamp=TS,
                                symbol=BTC_IDX, side=Side.BUY)
    assert generated.isalnum()
    assert len(generated) <= 36


def test_replanning_a_cycle_reuses_the_same_ids():
    # This is what makes reconciling an unconfirmed submission safe: the venue
    # rejects the duplicate instead of opening a second position.
    strategy_id = uuid4()
    snap, book_ = market(), portfolio(equity="10000")
    first = planner().plan(strategy_id=strategy_id, snapshot=snap, portfolio=book_,
                           state=risk_state(), rules=SYMBOL_RULES)
    second = planner().plan(strategy_id=strategy_id, snapshot=snap, portfolio=book_,
                            state=risk_state(), rules=SYMBOL_RULES)
    assert [o.client_order_id for o in first.orders.orders] == [
        o.client_order_id for o in second.orders.orders]


def test_different_strategies_get_different_ids():
    snap, book_ = market(), portfolio(equity="10000")
    a = planner().plan(strategy_id=uuid4(), snapshot=snap, portfolio=book_,
                       state=risk_state(), rules=SYMBOL_RULES)
    b = planner().plan(strategy_id=uuid4(), snapshot=snap, portfolio=book_,
                       state=risk_state(), rules=SYMBOL_RULES)
    assert {o.client_order_id for o in a.orders.orders}.isdisjoint(
        o.client_order_id for o in b.orders.orders)
