from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.risk import RiskState
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHalt
from tarakdingdung.infrastructure.algorithm.risk.overlay import StandardRiskOverlay
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCap


def _state(daily_pnl=Decimal("0")):
    return RiskState(
        equity=Decimal("1000"),
        daily_pnl=daily_pnl,
        volatility=0.0,
        symbol_venues={"btc": "indodax"},
    )


def test_overlay_applies_rules_in_sequence():
    overlay = StandardRiskOverlay([PerPositionCap(0.3), DailyLossHalt(Decimal("50"))])
    result = overlay.apply([Weight("btc", 0.8)], _state())
    assert result.halted is False
    assert result.weights == [Weight("btc", 0.3)]


def test_overlay_names_halting_rule():
    overlay = StandardRiskOverlay([PerPositionCap(0.3), DailyLossHalt(Decimal("50"))])
    result = overlay.apply([Weight("btc", 0.8)], _state(daily_pnl=Decimal("-100")))
    assert result.halted is True
    assert result.rule == "daily_loss_halt"
    assert result.weights == []


def test_overlay_returns_original_rule_name_when_passing():
    overlay = StandardRiskOverlay([PerPositionCap(0.3)])
    result = overlay.apply([Weight("btc", 0.1)], _state())
    assert result.halted is False
    assert result.weights == [Weight("btc", 0.1)]
