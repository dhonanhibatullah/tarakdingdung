from tarakdingdung.domain.contracts.algorithm.risk import RiskResult, RiskRule, RiskState
from tarakdingdung.domain.models.decision import Weight


class PerVenueCap(RiskRule):
    def __init__(self, max_weight: float) -> None:
        self._max_weight = max_weight

    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult:
        venue_totals: dict[str, float] = {}
        for w in weights:
            venue = state.symbol_venues.get(w.symbol_id, "unknown")
            venue_totals[venue] = venue_totals.get(venue, 0.0) + w.weight

        adjusted: list[Weight] = []
        for w in weights:
            venue = state.symbol_venues.get(w.symbol_id, "unknown")
            total = venue_totals[venue]
            if total > self._max_weight:
                scale = self._max_weight / total
                adjusted.append(Weight(w.symbol_id, w.weight * scale))
            else:
                adjusted.append(w)
        return RiskResult(weights=adjusted, halted=False, rule="per_venue_cap")
