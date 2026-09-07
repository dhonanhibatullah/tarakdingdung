from tarakdingdung.infrastructure.algorithm.risk.composite import CompositeRiskRule
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.drawdown_halt import DrawdownHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.halt_flag import HaltFlagRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_asset_cap import PerAssetCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_venue_cap import PerVenueCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import (
    VolatilityKillSwitchRiskRule,
)


def default_overlay(*, max_position: float = 0.25, max_asset: float = 0.35,
                    max_venue: float = 0.30, max_volatility: float = 0.15,
                    max_drawdown: float = 0.20,
                    max_daily_loss: float = 0.05) -> CompositeRiskRule:
    """The always-on overlay from summary 004 §4, in the order it must run.

    Caps first, halts last: a halt returns empty weights, so running it before
    the caps would leave them with nothing to do and hide whether they work.
    """
    return CompositeRiskRule((
        PerPositionCapRiskRule(max_weight=max_position),
        PerAssetCapRiskRule(max_weight=max_asset),
        PerVenueCapRiskRule(max_weight=max_venue),
        VolatilityKillSwitchRiskRule(max_volatility=max_volatility),
        DrawdownHaltRiskRule(max_drawdown=max_drawdown),
        DailyLossHaltRiskRule(max_daily_loss=max_daily_loss),
        HaltFlagRiskRule(),
    ))
