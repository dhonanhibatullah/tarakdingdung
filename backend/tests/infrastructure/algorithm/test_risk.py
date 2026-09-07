import pytest

from tarakdingdung.domain.models.algorithm import TargetWeights
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
from tests.infrastructure.algorithm.conformance import (
    BTC_IDX, BTC_TKO, ETH_IDX, TS, portfolio, risk_state,
)


def weights(mapping) -> TargetWeights:
    return TargetWeights(timestamp=TS, weights=mapping)


def test_per_venue_cap_scales_a_breaching_venue_proportionally():
    capped = PerVenueCapRiskRule(max_weight=0.30).apply(
        weights({BTC_IDX: 0.6, ETH_IDX: 0.2, BTC_TKO: 0.2}),
        portfolio(), risk_state())
    assert capped.weights[BTC_IDX] + capped.weights[ETH_IDX] == pytest.approx(0.30)
    # The shape the allocator chose is preserved: 3:1 before and after.
    assert capped.weights[BTC_IDX] / capped.weights[ETH_IDX] == pytest.approx(3.0)
    # An untouched venue is left alone.
    assert capped.weights[BTC_TKO] == pytest.approx(0.2)


def test_per_venue_cap_leaves_a_compliant_book_untouched():
    original = weights({BTC_IDX: 0.2, BTC_TKO: 0.2})
    capped = PerVenueCapRiskRule(max_weight=0.30).apply(
        original, portfolio(), risk_state())
    assert capped.weights == original.weights


def test_per_asset_cap_aggregates_the_same_coin_across_venues():
    # Holding BTC on both exchanges is one bet on BTC, not two.
    capped = PerAssetCapRiskRule(max_weight=0.30).apply(
        weights({BTC_IDX: 0.3, BTC_TKO: 0.3}), portfolio(), risk_state())
    assert capped.weights[BTC_IDX] + capped.weights[BTC_TKO] == pytest.approx(0.30)


def test_per_position_cap_clamps_each_leg():
    capped = PerPositionCapRiskRule(max_weight=0.2).apply(
        weights({BTC_IDX: 0.5, ETH_IDX: 0.1}), portfolio(), risk_state())
    assert capped.weights[BTC_IDX] == pytest.approx(0.2)
    assert capped.weights[ETH_IDX] == pytest.approx(0.1)


def test_per_position_cap_clamps_shorts_symmetrically():
    capped = PerPositionCapRiskRule(max_weight=0.2).apply(
        weights({BTC_IDX: -0.5}), portfolio(), risk_state())
    assert capped.weights[BTC_IDX] == pytest.approx(-0.2)


def test_volatility_kill_switch_flattens_above_the_threshold():
    rule = VolatilityKillSwitchRiskRule(max_volatility=0.15)
    held = weights({BTC_IDX: 0.5})
    assert rule.apply(held, portfolio(), risk_state(volatility=0.1)).weights != {}
    assert rule.apply(held, portfolio(), risk_state(volatility=0.9)).weights == {}


def test_drawdown_halt_measures_against_the_peak():
    rule = DrawdownHaltRiskRule(max_drawdown=0.20)
    held = weights({BTC_IDX: 0.2})
    assert rule.apply(held, portfolio(equity="9000"), risk_state()).weights != {}
    assert rule.apply(held, portfolio(equity="7000"), risk_state()).weights == {}


def test_drawdown_halt_ignores_a_meaningless_peak():
    rule = DrawdownHaltRiskRule(max_drawdown=0.20)
    held = weights({BTC_IDX: 0.2})
    assert rule.apply(held, portfolio(), risk_state(equity_peak="0")).weights != {}


def test_daily_loss_halt_is_relative_to_equity():
    rule = DailyLossHaltRiskRule(max_daily_loss=0.05)
    held = weights({BTC_IDX: 0.2})
    assert rule.apply(held, portfolio(), risk_state(daily_pnl="-400")).weights != {}
    assert rule.apply(held, portfolio(), risk_state(daily_pnl="-600")).weights == {}


def test_daily_loss_halt_ignores_profit():
    rule = DailyLossHaltRiskRule(max_daily_loss=0.05)
    held = weights({BTC_IDX: 0.2})
    assert rule.apply(held, portfolio(), risk_state(daily_pnl="5000")).weights != {}


def test_halt_flag_overrides_everything():
    assert HaltFlagRiskRule().apply(
        weights({BTC_IDX: 0.2}), portfolio(), risk_state(halted=True)).weights == {}


def test_composite_applies_every_rule_in_order():
    composite = CompositeRiskRule((
        PerPositionCapRiskRule(max_weight=0.4),
        PerVenueCapRiskRule(max_weight=0.3)))
    capped = composite.apply(weights({BTC_IDX: 0.9}), portfolio(), risk_state())
    assert capped.weights[BTC_IDX] == pytest.approx(0.3)


def test_composite_nests():
    inner = CompositeRiskRule((PerPositionCapRiskRule(max_weight=0.4),))
    outer = CompositeRiskRule((inner, PerVenueCapRiskRule(max_weight=0.3)))
    assert outer.apply(weights({BTC_IDX: 0.9}), portfolio(),
                       risk_state()).weights[BTC_IDX] == pytest.approx(0.3)


def test_default_overlay_caps_before_it_halts():
    # A halt returns nothing, so if it ran first the caps would be untestable.
    overlay = default_overlay()
    survived = overlay.apply(weights({BTC_IDX: 0.9}), portfolio(), risk_state())
    assert survived.weights[BTC_IDX] == pytest.approx(0.25)


def test_default_overlay_halts_on_any_tripped_condition():
    overlay = default_overlay()
    held = weights({BTC_IDX: 0.2})
    for state in (risk_state(halted=True), risk_state(volatility=0.9),
                  risk_state(daily_pnl="-9000")):
        assert overlay.apply(held, portfolio(), state).weights == {}
