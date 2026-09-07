from abc import abstractmethod

from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState

# A rule only acts when the breach is larger than floating-point noise.
# Without this, a rule that scales a group down to exactly its cap could see a
# residual overshoot on the next pass and scale again, breaking idempotence.
_BREACH = 1e-12


def _flat(weights: TargetWeights) -> TargetWeights:
    return TargetWeights(timestamp=weights.timestamp, weights={})


class GroupCapRiskRule(RiskRule):
    """Caps the gross exposure of each group, scaling a breaching group down.

    Scaling proportionally rather than truncating the largest position keeps
    the relative shape the allocator chose; the cap decides how much risk, not
    which risk.
    """

    def __init__(self, *, max_weight: float) -> None:
        self._max = max_weight

    @abstractmethod
    def _key(self, symbol: Symbol) -> object: ...

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        gross: dict[object, float] = {}
        for symbol, weight in weights.weights.items():
            key = self._key(symbol)
            gross[key] = gross.get(key, 0.0) + abs(weight)
        breaching = {k: self._max / v for k, v in gross.items()
                     if v > self._max * (1.0 + _BREACH) and v > 0}
        if not breaching:
            return weights
        scaled = {symbol: weight * breaching.get(self._key(symbol), 1.0)
                  for symbol, weight in weights.weights.items()}
        return TargetWeights(timestamp=weights.timestamp, weights=scaled)


class PerVenueCapRiskRule(GroupCapRiskRule):
    """Caps exposure to any one exchange.

    The default of 30% is the research's counterparty limit: an exchange can
    fail outright, and the rest of the book has to survive it.
    """

    def __init__(self, *, max_weight: float = 0.30) -> None:
        super().__init__(max_weight=max_weight)

    def _key(self, symbol: Symbol) -> object:
        return symbol.venue


class PerAssetCapRiskRule(GroupCapRiskRule):
    """Caps exposure to any one coin, aggregated across venues.

    Holding BTC on both exchanges is one bet on BTC, not two, and a per-symbol
    cap would quietly let it double.
    """

    def _key(self, symbol: Symbol) -> object:
        return symbol.base


class PerPositionCapRiskRule(RiskRule):
    """Clamps any single position to a maximum absolute weight."""

    def __init__(self, *, max_weight: float) -> None:
        self._max = max_weight

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        clamped = {symbol: max(-self._max, min(self._max, weight))
                   for symbol, weight in weights.weights.items()}
        return TargetWeights(timestamp=weights.timestamp, weights=clamped)


class HaltFlagRiskRule(RiskRule):
    """Honours an externally set halt: hold nothing while it stands."""

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        return _flat(weights) if state.halted else weights


class VolatilityKillSwitchRiskRule(RiskRule):
    """De-risks entirely when realised volatility exceeds a threshold.

    Returns empty weights rather than raising, because a halt is a decision
    that belongs in the equity curve as a flat period.
    """

    def __init__(self, *, max_volatility: float) -> None:
        self._max = max_volatility

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        return _flat(weights) if state.realized_volatility > self._max else weights


class DrawdownHaltRiskRule(RiskRule):
    """Stops trading once the drawdown budget is spent.

    The budget is fixed in advance, per the research: a drawdown limit chosen
    while losing money is not a limit.
    """

    def __init__(self, *, max_drawdown: float) -> None:
        self._max = max_drawdown

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        peak = float(state.equity_peak)
        if peak <= 0:
            return weights
        drawdown = (peak - float(portfolio.equity)) / peak
        return _flat(weights) if drawdown > self._max else weights


class DailyLossHaltRiskRule(RiskRule):
    """Flattens for the day once the daily loss limit is breached."""

    def __init__(self, *, max_daily_loss: float) -> None:
        self._max = max_daily_loss

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        equity = float(portfolio.equity)
        if equity <= 0:
            return _flat(weights)
        loss = -float(state.daily_pnl) / equity
        return _flat(weights) if loss > self._max else weights


class CompositeRiskRule(RiskRule):
    """Applies rules in order, and is itself a rule.

    Every constituent contracts weights toward zero and never expands them, so
    the composition inherits idempotence from its parts.
    """

    def __init__(self, rules: tuple[RiskRule, ...]) -> None:
        self._rules = rules

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        for rule in self._rules:
            weights = rule.apply(weights, portfolio, state)
        return weights


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
