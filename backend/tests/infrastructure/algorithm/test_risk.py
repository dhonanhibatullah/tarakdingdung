from decimal import Decimal

import pytest

from tarakdingdung.domain.contracts.algorithm.risk import RiskState
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHalt
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCap
from tarakdingdung.infrastructure.algorithm.risk.per_venue_cap import PerVenueCap
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import (
    VolatilityKillSwitch,
)


def state(volatility=0.0, daily_pnl=Decimal("0")):
    return RiskState(
        equity=Decimal("1000"),
        daily_pnl=daily_pnl,
        volatility=volatility,
        symbol_venues={"btc": "indodax", "eth": "indodax"},
    )


RULES = [
    (PerPositionCap(0.3), [Weight("btc", 0.8)], state()),
    (PerVenueCap(0.5), [Weight("btc", 0.4), Weight("eth", 0.4)], state()),
    (DailyLossHalt(Decimal("50")), [Weight("btc", 0.5)], state(daily_pnl=Decimal("-100"))),
    (VolatilityKillSwitch(1.0), [Weight("btc", 0.5)], state(volatility=1.5)),
]


@pytest.mark.parametrize("rule,weights,risk_state", RULES)
def test_rule_is_idempotent(rule, weights, risk_state):
    once = rule.apply(weights, risk_state)
    twice = rule.apply(once.weights, risk_state)
    assert twice.weights == once.weights
    assert twice.halted == once.halted


@pytest.mark.parametrize(
    "rule,risk_state",
    [
        (DailyLossHalt(Decimal("50")), state(daily_pnl=Decimal("-100"))),
        (VolatilityKillSwitch(1.0), state(volatility=1.5)),
    ],
)
def test_halt_liquidates(rule, risk_state):
    result = rule.apply([Weight("btc", 0.5)], risk_state)
    assert result.halted is True
    assert result.weights == []
    assert result.rule


def test_per_position_cap_does_not_renormalize():
    rule = PerPositionCap(0.3)
    result = rule.apply([Weight("btc", 0.8), Weight("eth", 0.2)], state())
    assert result.weights == [Weight("btc", 0.3), Weight("eth", 0.2)]
