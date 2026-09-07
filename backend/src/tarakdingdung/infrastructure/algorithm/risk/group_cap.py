from abc import abstractmethod

from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState

# A rule only acts when the breach is larger than floating-point noise. Without
# this, a rule that scales a group down to exactly its cap could see a residual
# overshoot on the next pass and scale again, breaking idempotence.
_BREACH = 1e-12


class GroupCapRiskRule(RiskRule):
    """Caps the gross exposure of each group, scaling a breaching group down.

    Scaling proportionally rather than truncating the largest position keeps
    the relative shape the allocator chose: the cap decides how much risk, not
    which risk.

    Subclasses supply the grouping key. The base class is where idempotence is
    guaranteed, so a new cap dimension inherits it rather than re-deriving it.
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
        return TargetWeights(
            timestamp=weights.timestamp,
            weights={symbol: weight * breaching.get(self._key(symbol), 1.0)
                     for symbol, weight in weights.weights.items()})
