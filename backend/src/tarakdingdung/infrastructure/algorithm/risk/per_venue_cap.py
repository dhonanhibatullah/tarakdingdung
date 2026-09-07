from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.algorithm.risk.group_cap import GroupCapRiskRule


class PerVenueCapRiskRule(GroupCapRiskRule):
    """Caps exposure to any one exchange.

    The default of 30% is the research's counterparty limit: an exchange can
    fail outright, and the rest of the book has to survive it.
    """

    def __init__(self, *, max_weight: float = 0.30) -> None:
        super().__init__(max_weight=max_weight)

    def _key(self, symbol: Symbol) -> object:
        return symbol.venue
