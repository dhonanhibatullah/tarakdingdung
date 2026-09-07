from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.algorithm.risk.group_cap import GroupCapRiskRule


class PerAssetCapRiskRule(GroupCapRiskRule):
    """Caps exposure to any one coin, aggregated across venues.

    Holding BTC on both exchanges is one bet on BTC, not two, and a per-symbol
    cap would quietly let it double.
    """

    def _key(self, symbol: Symbol) -> object:
        return symbol.base
