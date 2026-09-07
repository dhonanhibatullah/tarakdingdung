from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import OrderType, TimeInForce
from tarakdingdung.infrastructure.algorithm.allocation.conviction_weighted import (
    ConvictionWeightedAllocator,
)
from tarakdingdung.infrastructure.algorithm.allocation.equal_weight import EqualWeightAllocator
from tarakdingdung.infrastructure.algorithm.cost.depth_walk import DepthWalkCostModel
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFeeCostModel
from tarakdingdung.infrastructure.algorithm.order.venue_rule import VenueRuleOrderPlanner
from tarakdingdung.infrastructure.algorithm.risk.composite import CompositeRiskRule
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.drawdown_halt import DrawdownHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.halt_flag import HaltFlagRiskRule
from tarakdingdung.infrastructure.algorithm.risk.overlay import default_overlay
from tarakdingdung.infrastructure.algorithm.risk.per_asset_cap import PerAssetCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_venue_cap import PerVenueCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import (
    VolatilityKillSwitchRiskRule,
)
from tests.infrastructure.algorithm import conformance

RISK_RULES = [
    PerPositionCapRiskRule(max_weight=0.25),
    PerAssetCapRiskRule(max_weight=0.35),
    PerVenueCapRiskRule(max_weight=0.30),
    VolatilityKillSwitchRiskRule(max_volatility=0.15),
    DrawdownHaltRiskRule(max_drawdown=0.20),
    DailyLossHaltRiskRule(max_daily_loss=0.05),
    HaltFlagRiskRule(),
    CompositeRiskRule((PerVenueCapRiskRule(max_weight=0.30),
                       PerPositionCapRiskRule(max_weight=0.2))),
    default_overlay(),
]

HALTING_RULES = [HaltFlagRiskRule(), default_overlay()]

ALLOCATORS = [
    EqualWeightAllocator(),
    EqualWeightAllocator(max_gross=0.5, max_positions=2),
    ConvictionWeightedAllocator(),
    ConvictionWeightedAllocator(max_gross=0.8, max_positions=3),
]

COST_MODELS = [
    FlatFeeCostModel(fee_rate=Decimal("0.002")),
    FlatFeeCostModel(fee_rate=Decimal("0.002"), slippage_rate=Decimal("0.001")),
    DepthWalkCostModel(fee_rate=Decimal("0.002")),
]

ORDER_PLANNERS = [
    VenueRuleOrderPlanner(),
    VenueRuleOrderPlanner(order_type=OrderType.MARKET, time_in_force=TimeInForce.IOC),
    VenueRuleOrderPlanner(order_type=OrderType.LIMIT_MAKER, time_in_force=TimeInForce.GTX),
]


def _name(obj) -> str:
    return type(obj).__name__


@pytest.mark.parametrize("rule", RISK_RULES, ids=_name)
def test_risk_rule_conforms(rule):
    conformance.assert_risk_rule_conforms(rule)


@pytest.mark.parametrize("rule", HALTING_RULES, ids=_name)
def test_halting_risk_rule_flattens(rule):
    conformance.assert_risk_rule_respects_halt(rule)


@pytest.mark.parametrize("allocator", ALLOCATORS, ids=_name)
def test_allocator_conforms(allocator):
    conformance.assert_allocator_conforms(allocator)


@pytest.mark.parametrize("allocator", ALLOCATORS, ids=_name)
def test_allocator_is_flat_without_signals(allocator):
    conformance.assert_allocator_is_flat_without_signals(allocator)


@pytest.mark.parametrize("model", COST_MODELS, ids=_name)
def test_cost_model_conforms(model):
    conformance.assert_cost_model_conforms(model)


@pytest.mark.parametrize("planner", ORDER_PLANNERS, ids=_name)
def test_order_planner_conforms(planner):
    conformance.assert_order_planner_conforms(planner)
