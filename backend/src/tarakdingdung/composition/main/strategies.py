"""Builds a runnable planner from a stored strategy configuration.

Built per config rather than once at startup: otherwise the engine could only
ever run the pipeline that was wired at boot, and StrategyManagement would be
decorative — enabling a strategy in the database would change nothing.

``kind`` names the shape and ``parameters`` tunes it, so a new strategy is a
row, while a genuinely new *shape* is a new entry in ``_BUILDERS``.
"""

from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cycle import CyclePlanner
from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.strategy import StrategyConfig
from tarakdingdung.infrastructure.algorithm.allocation.conviction_weighted import (
    ConvictionWeightedAllocator,
)
from tarakdingdung.infrastructure.algorithm.allocation.equal_weight import EqualWeightAllocator
from tarakdingdung.infrastructure.algorithm.cycle.standard import StandardCyclePlanner
from tarakdingdung.infrastructure.algorithm.feature.rolling_window import (
    RollingWindowFeatureExtractor,
)
from tarakdingdung.infrastructure.algorithm.order.venue_rule import VenueRuleOrderPlanner
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tarakdingdung.infrastructure.algorithm.risk.daily_loss_halt import DailyLossHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.drawdown_halt import DrawdownHaltRiskRule
from tarakdingdung.infrastructure.algorithm.risk.halt_flag import HaltFlagRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_asset_cap import PerAssetCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_venue_cap import PerVenueCapRiskRule
from tarakdingdung.infrastructure.algorithm.risk.volatility_kill_switch import (
    VolatilityKillSwitchRiskRule,
)
from tarakdingdung.infrastructure.algorithm.signal.cross_sectional_momentum import (
    CrossSectionalMomentumSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.signal.moving_average_cross import (
    MovingAverageCrossSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.strategy.buy_and_hold import BuyAndHoldStrategy
from tarakdingdung.infrastructure.algorithm.strategy.pipeline import PipelineStrategy
from tarakdingdung.infrastructure.algorithm.universe.static import StaticUniverseSelector


def build_planner(config: StrategyConfig, parameters: dict) -> CyclePlanner:
    """Assemble the planner for one strategy.

    The risk rules are assembled here as an ordered sequence rather than a
    single composite so the plan can name which rule halted it. Caps run before
    halts: a halt empties the weights, so running it first would leave the caps
    nothing to act on and hide whether they work.
    """
    return StandardCyclePlanner(
        strategy=_strategy(config, parameters),
        risk_rules=_risk_rules(parameters),
        rebalancer=NoTradeBandRebalancer(
            band=_float(parameters, "rebalance_band", 0.005)),
        order_planner=VenueRuleOrderPlanner())


def _strategy(config: StrategyConfig, parameters: dict) -> Strategy:
    builder = _BUILDERS.get(config.kind)
    if builder is None:
        raise DomainError(
            f"unknown strategy kind {config.kind!r}; expected one of "
            f"{', '.join(sorted(_BUILDERS))}", ErrorType.BAD_ARGS)
    return builder(config, parameters)


def _pipeline(config: StrategyConfig, parameters: dict) -> Strategy:
    return PipelineStrategy(
        universe=StaticUniverseSelector(config.universe),
        features=RollingWindowFeatureExtractor(
            momentum_window=_int(parameters, "momentum_window", 30),
            fast_window=_int(parameters, "fast_window", 10),
            slow_window=_int(parameters, "slow_window", 30),
            volatility_window=_int(parameters, "volatility_window", 30)),
        signals=_signal(parameters),
        allocator=_allocator(parameters))


def _buy_and_hold(config: StrategyConfig, parameters: dict) -> Strategy:
    return BuyAndHoldStrategy(config.universe,
                              max_gross=_float(parameters, "max_gross", 1.0))


_BUILDERS = {"pipeline": _pipeline, "buy_and_hold": _buy_and_hold}


def _signal(parameters: dict):
    # Long-only by default: neither venue supports shorting, so a negative
    # weight would describe a position we cannot hold.
    long_only = bool(parameters.get("long_only", True))
    kind = parameters.get("signal", "momentum")
    if kind == "moving_average_cross":
        return MovingAverageCrossSignalGenerator(long_only=long_only)
    if kind == "momentum":
        return CrossSectionalMomentumSignalGenerator(long_only=long_only)
    raise DomainError(f"unknown signal {kind!r}", ErrorType.BAD_ARGS)


def _allocator(parameters: dict):
    max_gross = _float(parameters, "max_gross", 1.0)
    max_positions = parameters.get("max_positions")
    kind = parameters.get("allocator", "equal_weight")
    if kind == "conviction_weighted":
        return ConvictionWeightedAllocator(max_gross=max_gross,
                                           max_positions=max_positions)
    if kind == "equal_weight":
        return EqualWeightAllocator(max_gross=max_gross, max_positions=max_positions)
    raise DomainError(f"unknown allocator {kind!r}", ErrorType.BAD_ARGS)


def _risk_rules(parameters: dict) -> tuple[RiskRule, ...]:
    return (
        PerPositionCapRiskRule(max_weight=_float(parameters, "max_position", 0.25)),
        PerAssetCapRiskRule(max_weight=_float(parameters, "max_asset", 0.35)),
        PerVenueCapRiskRule(max_weight=_float(parameters, "max_venue", 0.30)),
        VolatilityKillSwitchRiskRule(
            max_volatility=_float(parameters, "max_volatility", 0.15)),
        DrawdownHaltRiskRule(max_drawdown=_float(parameters, "max_drawdown", 0.20)),
        DailyLossHaltRiskRule(max_daily_loss=_float(parameters, "max_daily_loss", 0.05)),
        HaltFlagRiskRule(),
    )


def _float(parameters: dict, key: str, default: float) -> float:
    value = parameters.get(key)
    if value is None:
        return default
    try:
        # Via Decimal so a JSON string is accepted as readily as a number.
        return float(Decimal(str(value)))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise DomainError(f"strategy parameter {key!r} is not a number: {value!r}",
                          ErrorType.BAD_ARGS, exc) from exc


def _int(parameters: dict, key: str, default: int) -> int:
    value = parameters.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise DomainError(f"strategy parameter {key!r} is not an integer: {value!r}",
                          ErrorType.BAD_ARGS, exc) from exc
